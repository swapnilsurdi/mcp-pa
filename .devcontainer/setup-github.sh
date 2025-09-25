#!/bin/bash

echo "🔧 Setting up GitHub authentication..."

# Check if GitHub environment variables are set
if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_USER" ] || [ -z "$GITHUB_EMAIL" ]; then
    echo "⚠️  GitHub environment variables not set."
    echo "Please set the following environment variables:"
    echo "  - GITHUB_TOKEN: Your GitHub personal access token"
    echo "  - GITHUB_USER: Your GitHub username"
    echo "  - GITHUB_EMAIL: Your GitHub email"
    echo ""
    echo "You can create a personal access token at:"
    echo "https://github.com/settings/tokens"
    echo ""
    echo "Then set them in your shell profile or .env file"
else
    # Configure git with user info
    git config --global user.name "$GITHUB_USER"
    git config --global user.email "$GITHUB_EMAIL"
    
    # Configure GitHub CLI authentication
    echo "$GITHUB_TOKEN" | gh auth login --with-token
    
    # Set up git credential helper to use the token
    git config --global credential.helper '!f() { echo "username=$GITHUB_USER"; echo "password=$GITHUB_TOKEN"; }; f'
    
    # Configure some useful git aliases
    git config --global alias.co checkout
    git config --global alias.br branch
    git config --global alias.ci commit
    git config --global alias.st status
    git config --global alias.last 'log -1 HEAD'
    git config --global alias.visual '!gitk'
    
    # Set up delta as the diff pager if available
    if command -v delta &> /dev/null; then
        git config --global core.pager delta
        git config --global interactive.diffFilter 'delta --color-only'
        git config --global delta.navigate true
        git config --global delta.light false
        git config --global delta.side-by-side true
        git config --global delta.line-numbers true
    fi
    
    echo "✅ GitHub authentication configured successfully!"
    echo "   User: $GITHUB_USER"
    echo "   Email: $GITHUB_EMAIL"
    
    # Verify GitHub CLI authentication
    echo ""
    echo "🔍 Verifying GitHub CLI authentication..."
    gh auth status
fi

echo ""
echo "📦 Development container ready!"