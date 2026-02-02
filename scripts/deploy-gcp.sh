#!/bin/bash
# AI News Aggregator - GCP Deployment Script
# This script automates the initial setup and deployment to Google Cloud Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_prerequisites() {
    echo_info "Checking prerequisites..."

    if ! command -v gcloud &> /dev/null; then
        echo_error "gcloud CLI is not installed. Please install it first."
        echo "Visit: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    if ! command -v terraform &> /dev/null; then
        echo_error "Terraform is not installed. Please install it first."
        echo "Visit: https://developer.hashicorp.com/terraform/downloads"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed. Please install it first."
        exit 1
    fi

    echo_info "All prerequisites met."
}

# Get project ID from user
get_project_id() {
    if [ -z "$PROJECT_ID" ]; then
        echo ""
        echo "Enter your GCP Project ID (or set PROJECT_ID env var):"
        read -r PROJECT_ID
    fi

    if [ -z "$PROJECT_ID" ]; then
        echo_error "Project ID is required."
        exit 1
    fi

    export PROJECT_ID
    echo_info "Using project: $PROJECT_ID"
}

# Configure gcloud
configure_gcloud() {
    echo_info "Configuring gcloud..."

    # Check if already authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        echo_warn "Not authenticated to gcloud. Running authentication..."
        gcloud auth login
    fi

    gcloud config set project "$PROJECT_ID"

    # Verify billing is enabled
    BILLING_ENABLED=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingEnabled)" 2>/dev/null || echo "false")
    if [ "$BILLING_ENABLED" != "True" ]; then
        echo_error "Billing is not enabled for project $PROJECT_ID"
        echo "Please enable billing at: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
        exit 1
    fi

    echo_info "Billing is enabled."
}

# Enable required APIs
enable_apis() {
    echo_info "Enabling required GCP APIs (this may take a few minutes)..."

    APIS=(
        "run.googleapis.com"
        "sqladmin.googleapis.com"
        "redis.googleapis.com"
        "secretmanager.googleapis.com"
        "cloudbuild.googleapis.com"
        "artifactregistry.googleapis.com"
        "compute.googleapis.com"
        "vpcaccess.googleapis.com"
        "cloudscheduler.googleapis.com"
        "aiplatform.googleapis.com"
        "gmail.googleapis.com"
        "iamcredentials.googleapis.com"
    )

    for api in "${APIS[@]}"; do
        echo "  Enabling $api..."
        gcloud services enable "$api" --quiet
    done

    echo_info "All APIs enabled."
}

# Create Artifact Registry repository
create_artifact_registry() {
    echo_info "Creating Artifact Registry repository..."

    if gcloud artifacts repositories describe ai-news-images --location=us-central1 &> /dev/null; then
        echo_info "Artifact Registry repository already exists."
    else
        gcloud artifacts repositories create ai-news-images \
            --repository-format=docker \
            --location=us-central1 \
            --description="Docker images for AI News Aggregator"
        echo_info "Artifact Registry repository created."
    fi
}

# Create GCS bucket for Terraform state
create_terraform_state_bucket() {
    echo_info "Creating Terraform state bucket..."

    BUCKET_NAME="${PROJECT_ID}-tfstate"

    if gsutil ls "gs://$BUCKET_NAME" &> /dev/null; then
        echo_info "Terraform state bucket already exists."
    else
        gsutil mb -l us-central1 "gs://$BUCKET_NAME"
        gsutil versioning set on "gs://$BUCKET_NAME"
        echo_info "Terraform state bucket created: gs://$BUCKET_NAME"
    fi

    # Update terraform backend configuration
    echo_info "Updating Terraform backend configuration..."
    sed -i.bak "s/bucket = \"ai-news-aggregator-tfstate\"/bucket = \"$BUCKET_NAME\"/" infra/terraform/main.tf
    rm -f infra/terraform/main.tf.bak
}

# Configure Cloud Build permissions
configure_cloud_build_permissions() {
    echo_info "Configuring Cloud Build permissions..."

    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

    ROLES=(
        "roles/run.admin"
        "roles/iam.serviceAccountUser"
        "roles/secretmanager.secretAccessor"
    )

    for role in "${ROLES[@]}"; do
        echo "  Granting $role to Cloud Build service account..."
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$CLOUD_BUILD_SA" \
            --role="$role" \
            --quiet
    done

    echo_info "Cloud Build permissions configured."
}

# Generate secrets
generate_secrets() {
    echo_info "Generating secrets..."

    DJANGO_SECRET=$(openssl rand -base64 50 | tr -d '\n')
    ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '\n')
    NEXTAUTH_SECRET=$(openssl rand -base64 32 | tr -d '\n')
    DB_PASSWORD=$(openssl rand -base64 24 | tr -d '\n')

    echo_info "Secrets generated. Creating in Secret Manager..."

    # Create secrets in Secret Manager
    create_secret "django-secret-key" "$DJANGO_SECRET"
    create_secret "encryption-key" "$ENCRYPTION_KEY"
    create_secret "nextauth-secret" "$NEXTAUTH_SECRET"
    create_secret "database-password" "$DB_PASSWORD"

    # Export for Terraform
    export TF_VAR_django_secret_key="$DJANGO_SECRET"
    export TF_VAR_encryption_key="$ENCRYPTION_KEY"
    export TF_VAR_nextauth_secret="$NEXTAUTH_SECRET"
    export TF_VAR_database_password="$DB_PASSWORD"

    echo_info "Secrets created in Secret Manager."
    echo_warn "You still need to add Google OAuth credentials and Google API key manually."
}

create_secret() {
    local secret_name=$1
    local secret_value=$2

    if gcloud secrets describe "$secret_name" &> /dev/null; then
        echo "  Secret $secret_name already exists, adding new version..."
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
    else
        echo "  Creating secret $secret_name..."
        echo -n "$secret_value" | gcloud secrets create "$secret_name" --data-file=-
    fi
}

# Prompt for manual secrets
prompt_for_manual_secrets() {
    echo ""
    echo_warn "Manual secrets required:"
    echo "  1. Google OAuth Client ID and Secret (from Google Cloud Console)"
    echo "  2. Google API Key for Gemini (from Google AI Studio)"
    echo ""

    if [ -z "$GOOGLE_OAUTH_CLIENT_ID" ]; then
        echo "Enter Google OAuth Client ID (or press Enter to skip for now):"
        read -r GOOGLE_OAUTH_CLIENT_ID
    fi

    if [ -n "$GOOGLE_OAUTH_CLIENT_ID" ]; then
        if [ -z "$GOOGLE_OAUTH_CLIENT_SECRET" ]; then
            echo "Enter Google OAuth Client Secret:"
            read -rs GOOGLE_OAUTH_CLIENT_SECRET
            echo ""
        fi

        create_secret "google-oauth-client-id" "$GOOGLE_OAUTH_CLIENT_ID"
        create_secret "google-oauth-client-secret" "$GOOGLE_OAUTH_CLIENT_SECRET"

        export TF_VAR_google_oauth_client_id="$GOOGLE_OAUTH_CLIENT_ID"
        export TF_VAR_google_oauth_secret="$GOOGLE_OAUTH_CLIENT_SECRET"
    fi

    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "Enter Google API Key for Gemini (or press Enter to skip for now):"
        read -rs GOOGLE_API_KEY
        echo ""
    fi

    if [ -n "$GOOGLE_API_KEY" ]; then
        create_secret "google-api-key" "$GOOGLE_API_KEY"
        export TF_VAR_google_api_key="$GOOGLE_API_KEY"
    fi
}

# Update terraform.tfvars with project ID
update_terraform_vars() {
    echo_info "Updating terraform.tfvars..."

    TFVARS_FILE="infra/terraform/terraform.tfvars"

    sed -i.bak "s/YOUR_PROJECT_ID/$PROJECT_ID/g" "$TFVARS_FILE"
    rm -f "$TFVARS_FILE.bak"

    echo_info "terraform.tfvars updated with project ID: $PROJECT_ID"
}

# Initialize and apply Terraform
run_terraform() {
    echo_info "Running Terraform..."

    cd infra/terraform

    # Initialize Terraform
    echo_info "Initializing Terraform..."
    terraform init -reconfigure

    # Plan
    echo_info "Planning Terraform changes..."
    terraform plan -out=tfplan

    echo ""
    echo_warn "Review the Terraform plan above."
    echo "Do you want to apply these changes? (yes/no)"
    read -r APPLY_CONFIRM

    if [ "$APPLY_CONFIRM" == "yes" ]; then
        echo_info "Applying Terraform..."
        terraform apply tfplan
        echo_info "Terraform applied successfully."
    else
        echo_warn "Terraform apply skipped."
    fi

    cd ../..
}

# Build and push initial Docker images
build_and_push_images() {
    echo_info "Building and pushing Docker images..."

    # Configure Docker for Artifact Registry
    gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

    REGISTRY="us-central1-docker.pkg.dev/$PROJECT_ID/ai-news-images"

    # Build backend
    echo_info "Building backend image..."
    docker build -t "$REGISTRY/backend:latest" -f backend/Dockerfile backend/

    # Build worker
    echo_info "Building worker image..."
    docker build -t "$REGISTRY/worker:latest" -f backend/Dockerfile.worker backend/

    # Build frontend (with placeholder API URL for now)
    echo_info "Building frontend image..."
    docker build \
        --build-arg NEXT_PUBLIC_API_URL="https://placeholder.run.app/api" \
        -t "$REGISTRY/frontend:latest" \
        -f frontend/Dockerfile frontend/

    # Push images
    echo_info "Pushing images to Artifact Registry..."
    docker push "$REGISTRY/backend:latest"
    docker push "$REGISTRY/worker:latest"
    docker push "$REGISTRY/frontend:latest"

    echo_info "Images pushed successfully."
}

# Print next steps
print_next_steps() {
    echo ""
    echo "=========================================="
    echo_info "Deployment setup complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. If you haven't added Google OAuth credentials:"
    echo "   - Go to Google Cloud Console > APIs & Services > Credentials"
    echo "   - Create OAuth 2.0 credentials"
    echo "   - Add them to Secret Manager:"
    echo "     gcloud secrets versions add google-oauth-client-id --data-file=-"
    echo "     gcloud secrets versions add google-oauth-client-secret --data-file=-"
    echo ""
    echo "2. If you haven't added Google API Key for Gemini:"
    echo "   - Go to Google AI Studio (https://aistudio.google.com/app/apikey)"
    echo "   - Create an API key"
    echo "   - Add it to Secret Manager:"
    echo "     gcloud secrets versions add google-api-key --data-file=-"
    echo ""
    echo "3. Re-run Terraform with all secrets set:"
    echo "   cd infra/terraform && terraform apply"
    echo ""
    echo "4. Trigger a Cloud Build deployment:"
    echo "   gcloud builds submit --config=cloudbuild.yaml"
    echo ""
    echo "5. Get your deployed URLs:"
    echo "   gcloud run services describe ai-news-backend --region=us-central1 --format='value(status.url)'"
    echo "   gcloud run services describe ai-news-frontend --region=us-central1 --format='value(status.url)'"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "=========================================="
    echo "AI News Aggregator - GCP Deployment Setup"
    echo "=========================================="
    echo ""

    check_prerequisites
    get_project_id
    configure_gcloud
    enable_apis
    create_artifact_registry
    create_terraform_state_bucket
    configure_cloud_build_permissions
    generate_secrets
    prompt_for_manual_secrets
    update_terraform_vars

    echo ""
    echo "Do you want to build and push Docker images now? (yes/no)"
    read -r BUILD_IMAGES

    if [ "$BUILD_IMAGES" == "yes" ]; then
        build_and_push_images
    fi

    echo ""
    echo "Do you want to run Terraform now? (yes/no)"
    read -r RUN_TF

    if [ "$RUN_TF" == "yes" ]; then
        run_terraform
    fi

    print_next_steps
}

# Run main function
main "$@"
