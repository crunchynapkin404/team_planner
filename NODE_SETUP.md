# Node.js Setup Instructions

This project requires Node.js 18+ for the React frontend.

## Quick Setup

1. **Using nvm (recommended):**
   ```bash
   # Install nvm if you don't have it
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   
   # Use the project's Node.js version
   nvm use
   
   # Install dependencies
   cd frontend && npm install
   ```

2. **Using system Node.js:**
   - Make sure you have Node.js 18+ installed
   - Run: `cd frontend && npm install`

3. **In Alpine Linux dev container:**
   ```bash
   sudo apk add --no-cache nodejs npm
   cd frontend && npm install
   ```

## Running the Frontend

```bash
cd frontend
npm run dev  # Development server
npm run build  # Production build
```

The frontend will be available at http://localhost:5173
