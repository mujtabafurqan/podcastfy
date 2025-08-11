#!/bin/bash

echo "🚀 Deploying Podcastfy Extensions to Railway"
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Railway CLI is installed
print_step "🔧 Checking Railway CLI installation..."
if ! command -v railway &> /dev/null; then
    print_warning "Railway CLI not found. Installing..."
    
    # Check if npm is available
    if command -v npm &> /dev/null; then
        npm install -g @railway/cli
        print_success "Railway CLI installed via npm"
    else
        print_error "npm not found. Please install Node.js and npm first, then run:"
        echo "  npm install -g @railway/cli"
        exit 1
    fi
else
    print_success "Railway CLI is already installed"
fi

# Verify we're in the correct directory
if [[ ! -f "podcastfy/client.py" ]] || [[ ! -f "railway.json" ]]; then
    print_error "Please run this script from the podcastfy root directory"
    exit 1
fi

print_success "Found podcastfy project files"

# Login to Railway
print_step "🔐 Logging into Railway..."
print_warning "This will open your browser for authentication"
if ! railway login; then
    print_error "Railway login failed"
    exit 1
fi

print_success "Successfully logged into Railway"

# Check if project exists or create new one
print_step "📦 Setting up Railway project..."
if railway status &> /dev/null; then
    print_success "Using existing Railway project"
    railway status
else
    print_warning "Creating new Railway project..."
    railway init podcastfy-async
    print_success "Railway project 'podcastfy-async' created"
fi

# Add PostgreSQL database if not exists
print_step "🗄️  Setting up PostgreSQL database..."
if railway service list | grep -q "PostgreSQL"; then
    print_success "PostgreSQL database already exists"
else
    print_warning "Adding PostgreSQL database..."
    railway add postgresql
    print_success "PostgreSQL database added"
fi

# Set environment variables
print_step "🔧 Setting up environment variables..."
echo ""
echo "Please provide your API keys for deployment:"
echo "(Leave empty to skip if already set)"

read -p "Enter your OpenAI API Key (or press Enter to skip): " openai_key
if [[ ! -z "$openai_key" ]]; then
    railway variables set OPENAI_API_KEY="$openai_key"
    print_success "OpenAI API key set"
fi

read -p "Enter your Gemini API Key (or press Enter to skip): " gemini_key  
if [[ ! -z "$gemini_key" ]]; then
    railway variables set GEMINI_API_KEY="$gemini_key"
    print_success "Gemini API key set"
fi

# Set production environment
railway variables set NODE_ENV="production"
railway variables set PYTHONPATH="/app"

print_success "Environment variables configured"

# Deploy web service (async API)
print_step "🌐 Deploying web service..."
print_warning "This may take several minutes..."
if railway up --detach; then
    print_success "Web service deployed successfully"
else
    print_error "Web service deployment failed"
    exit 1
fi

# Create and deploy worker service
print_step "👷 Setting up worker service..."
if railway service list | grep -q "worker"; then
    print_success "Worker service already exists"
    railway service use worker
else
    print_warning "Creating worker service..."
    railway service create worker
    railway service use worker
    print_success "Worker service created"
fi

# Deploy worker service
print_step "⚙️ Deploying worker service..."
if railway up --detach; then
    print_success "Worker service deployed successfully"
else
    print_error "Worker service deployment failed"
    print_warning "You can retry with: railway service --service=worker up"
fi

# Show deployment status
print_step "📊 Deployment Status"
echo "===================="
railway status

# Get service URLs
print_step "🔗 Service Information"
echo "====================="
WEB_URL=$(railway service --service=web url 2>/dev/null || echo "Not available")
echo "Web Service URL: $WEB_URL"

# Final instructions
echo ""
print_success "🎉 Deployment completed!"
echo ""
echo "Next steps:"
echo "1. Check your Railway dashboard: https://railway.app/dashboard"
echo "2. Verify services are running: railway status"
echo "3. Check logs if needed: railway logs"
echo "4. Test your API endpoints:"
echo "   - Health check: ${WEB_URL}/api/health"
echo "   - Library: ${WEB_URL}/api/library"
echo ""
print_warning "Note: It may take a few minutes for services to fully start up"