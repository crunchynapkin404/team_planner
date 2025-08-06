# Team Planner Frontend

This is the React frontend for the Team Planner application, built with Vite, TypeScript, Material-UI, and Redux Toolkit.

## Technology Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Material-UI (MUI)** - Component library
- **Redux Toolkit** - State management
- **React Router** - Routing
- **Axios** - HTTP client

## Features

### ✅ Phase 4 Complete: Frontend Foundation

1. **Project Setup**
   - ✅ React + Vite setup with TypeScript
   - ✅ Material-UI integration with custom theme
   - ✅ Redux Toolkit configuration
   - ✅ API integration with Django backend

2. **Core Components**
   - ✅ Authentication system (LoginForm, PrivateRoute)
   - ✅ User dashboard with stats and activities
   - ✅ Navigation system (TopNavigation, SideNavigation)
   - ✅ Role-based UI rendering

3. **API Integration**
   - ✅ HTTP client setup with interceptors
   - ✅ Error handling and loading states
   - ✅ Token management
   - ✅ Authentication flow

## Project Structure

```
src/
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   └── PrivateRoute.tsx
│   └── layout/
│       ├── MainLayout.tsx
│       ├── SideNavigation.tsx
│       └── TopNavigation.tsx
├── hooks/
│   └── redux.ts
├── pages/
│   └── Dashboard.tsx
├── services/
│   ├── apiClient.ts
│   └── authService.ts
├── store/
│   ├── index.ts
│   └── slices/
│       └── authSlice.ts
├── types/
│   └── index.ts
├── App.tsx
├── main.tsx
├── theme.ts
└── index.css
```

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
```

This starts the development server at `http://localhost:3000` with proxy to Django backend at `http://localhost:8000`.

### Build

```bash
npm run build
```

Builds the app for production to the `../team_planner/static/react` directory.

### Linting

```bash
npm run lint
```

### Type Checking

```bash
npm run type-check
```

## API Integration

The frontend communicates with the Django backend through:

- **Authentication**: Token-based authentication
- **API Base URL**: `/api/` (proxied to Django in development)
- **Error Handling**: Centralized error handling with user feedback
- **Loading States**: Global loading states for better UX

## Authentication Flow

1. User enters credentials in LoginForm
2. Frontend calls Django `/api/auth-token/` endpoint
3. On success, token is stored and user data is fetched
4. Protected routes check authentication status
5. Token is automatically added to API requests

## Future Development

The following routes are set up but show placeholder content:

- `/employees` - Employee management
- `/schedules` - Schedule viewing and management
- `/swaps` - Shift swap requests
- `/leaves` - Leave request management
- `/settings` - Application settings

These will be implemented in subsequent phases of the project.

## Development Notes

- All components use TypeScript for type safety
- Material-UI provides consistent styling and responsive design
- Redux Toolkit manages global state with slices
- React Router handles client-side routing
- Axios interceptors handle authentication and error responses
- The build output integrates with Django's static file serving
