# Centralized Auth Service

A "Clerk-like" auth service for all of Jimmy's apps. Build once, use everywhere.

**Status:** Future project - build after Greg is modularized

---

## Vision

```
┌─────────────────────────────────────────────────────────────────┐
│                     JIMMY AUTH                                   │
│         One auth service for all your apps                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  • User registration & login                                    │
│  • JWT tokens (RS256 for local validation)                      │
│  • API key management                                           │
│  • Multi-app support                                            │
│  • App-specific roles & permissions                             │
│  • Password reset & email verification                          │
│  • OAuth (Google, GitHub)                                       │
│  • Simple admin dashboard                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │  Greg   │          │  Vocal  │          │ Future  │
   │         │          │         │          │  Apps   │
   └─────────┘          └─────────┘          └─────────┘
```

---

## Why Build This

| Problem | Solution |
|---------|----------|
| Repeat auth code in every app | Build once, import SDK |
| Separate user databases | Single user, access all apps |
| No SSO between apps | Shared sessions |
| Re-implement API keys each time | Centralized key management |
| Auth is boring but critical | Do it right once |

---

## What Exists in Greg (Starting Point)

Already built:
- ✅ User registration
- ✅ Password hashing (bcrypt)
- ✅ JWT access tokens
- ✅ Refresh tokens with rotation
- ✅ Session management
- ✅ API key generation & validation
- ✅ Role-based permissions (admin/user)
- ✅ Rate limiting

Need to add:
- ❌ Password reset flow
- ❌ Email verification
- ❌ Multi-app support
- ❌ App-specific roles
- ❌ OAuth providers
- ❌ Admin dashboard
- ❌ SDKs for easy integration

---

## API Design

### Public Endpoints (No Auth)

```
POST /auth/register
     Body: { email, password, app_slug? }
     Returns: { user, tokens }

POST /auth/login
     Body: { email, password }
     Returns: { access_token, refresh_token }

POST /auth/refresh
     Body: { refresh_token }
     Returns: { access_token, refresh_token }

POST /auth/forgot-password
     Body: { email }
     Returns: { message: "Check your email" }

POST /auth/reset-password
     Body: { token, new_password }
     Returns: { message: "Password updated" }

POST /auth/verify-email
     Body: { token }
     Returns: { message: "Email verified" }

GET /auth/oauth/:provider
     Redirects to OAuth provider

GET /auth/oauth/:provider/callback
     Handles OAuth callback, returns tokens
```

### Authenticated Endpoints

```
GET /auth/me
    Returns: { user, apps, roles }

POST /auth/logout
     Revokes current session

POST /auth/logout-all
     Revokes all sessions
```

### API Key Endpoints

```
POST /api-keys
     Body: { name, app_slug, permissions?, expires_at? }
     Returns: { key: "ja_sk_xxx...", id }  # Key shown once

GET /api-keys
    Returns: [{ id, name, app, last_used, created_at }]

DELETE /api-keys/:id
       Revokes key
```

### Validation Endpoints (For Other Services)

```
POST /validate
     Body: { token, app_slug }
     Returns: { valid, user, role, permissions }

GET /.well-known/jwks.json
    Returns: { keys: [...] }  # Public keys for local JWT validation
```

### Admin Endpoints (Dashboard)

```
# App Management
POST /apps
     Body: { name, slug, allowed_origins }

GET /apps

PATCH /apps/:id

# Role Management
POST /apps/:id/roles
     Body: { name, permissions }

# User Management
GET /admin/users
GET /admin/users/:id
PATCH /admin/users/:id
DELETE /admin/users/:id
```

---

## Database Schema

```sql
-- Core user table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- NULL if OAuth-only
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- OAuth connections
CREATE TABLE oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- 'google', 'github'
    provider_user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider, provider_user_id)
);

-- Registered applications
CREATE TABLE apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,  -- 'greg', 'vocal'
    allowed_origins TEXT[],  -- CORS
    webhook_url VARCHAR(500),  -- Notify on user events
    created_at TIMESTAMP DEFAULT NOW()
);

-- Roles defined per app
CREATE TABLE app_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id UUID REFERENCES apps(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,  -- 'admin', 'pro', 'free'
    permissions TEXT[],  -- ['read:*', 'write:projects']
    is_default BOOLEAN DEFAULT FALSE,  -- Assigned to new users
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(app_id, name)
);

-- User access to apps
CREATE TABLE user_apps (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID REFERENCES apps(id) ON DELETE CASCADE,
    role_id UUID REFERENCES app_roles(id),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, app_id)
);

-- Sessions (refresh tokens)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB,  -- { browser, os, ip }
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    app_id UUID REFERENCES apps(id) ON DELETE CASCADE,
    key_prefix VARCHAR(10) NOT NULL,  -- 'ja_sk_abc' (for identification)
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    permissions TEXT[],
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Password reset tokens
CREATE TABLE password_resets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Email verification tokens
CREATE TABLE email_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## JWT Structure

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "email_verified": true,
  "aud": "greg",
  "role": "pro",
  "permissions": ["read:*", "write:projects"],
  "iat": 1699999999,
  "exp": 1700000899
}
```

- **sub**: User ID
- **aud**: App slug (token only valid for this app)
- **role**: User's role in this app
- **permissions**: Flattened permissions array

---

## SDK Design

### Python SDK

```python
# Installation
# pip install jimmy-auth

# Initialize
from jimmy_auth import JimmyAuth

auth = JimmyAuth(
    service_url="https://auth.jimmypocock.com",
    app_slug="greg",
)

# FastAPI integration
from jimmy_auth.fastapi import AuthMiddleware, CurrentUser, require_permission

app.add_middleware(AuthMiddleware, auth=auth)

@app.get("/projects")
async def list_projects(user: CurrentUser):
    return await get_user_projects(user.id)

@app.delete("/admin/users/{id}")
@require_permission("admin:users")
async def delete_user(id: str, user: CurrentUser):
    ...
```

### JavaScript SDK

```typescript
// Installation
// npm install @jimmy/auth

// React integration
import { AuthProvider, useUser, SignIn, SignUp } from '@jimmy/auth/react'

function App() {
  return (
    <AuthProvider appSlug="greg">
      <MyApp />
    </AuthProvider>
  )
}

function Profile() {
  const { user, isLoaded, signOut } = useUser()

  if (!isLoaded) return <Loading />
  if (!user) return <SignIn />

  return <div>Hello {user.email}</div>
}

// API calls include token automatically
import { authFetch } from '@jimmy/auth'

const projects = await authFetch('/api/projects')
```

---

## Build Plan

### Phase 1: Core Service (Week 1)

```
Day 1-2: Set up new repo, extract auth from Greg
         - Users, sessions, JWT generation
         - Basic login/register endpoints

Day 3:   Password reset flow
         - Generate token, send email
         - Reset endpoint

Day 4:   Email verification
         - Send verification on register
         - Verify endpoint

Day 5:   Multi-app support
         - Apps table
         - User-app relationships
         - App-specific JWT audience
```

### Phase 2: Integration (Week 2)

```
Day 1:   API key management
         - Create, list, revoke
         - Validation endpoint

Day 2:   JWKS endpoint for local validation
         - Generate RS256 key pair
         - Publish public key

Day 3:   Python SDK
         - FastAPI middleware
         - Dependencies

Day 4:   Migrate Greg to use auth service
         - Test everything works

Day 5:   Deploy auth service
         - Railway/Fly.io
         - Custom domain
```

### Phase 3: Polish (Week 3)

```
Day 1-2: Admin dashboard
         - List users, apps, keys
         - Basic management

Day 3:   OAuth - Google
         - Register OAuth app
         - Implement flow

Day 4:   OAuth - GitHub

Day 5:   JavaScript SDK
         - React hooks
         - Auth fetch wrapper
```

---

## Deployment

```yaml
# docker-compose.yml
services:
  jimmy-auth:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      JWT_PRIVATE_KEY: ${JWT_PRIVATE_KEY}
      JWT_PUBLIC_KEY: ${JWT_PUBLIC_KEY}
      SMTP_HOST: ${SMTP_HOST}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine
```

---

## Security Considerations

- [ ] Rate limit all auth endpoints
- [ ] Hash all tokens before storing (bcrypt for passwords, SHA256 for others)
- [ ] Short-lived access tokens (15 min)
- [ ] Refresh token rotation
- [ ] Secure cookie options (httpOnly, secure, sameSite)
- [ ] CORS properly configured per app
- [ ] Audit log for sensitive actions
- [ ] Brute force protection (lockout after N failures)

---

## Cost Estimate

| Component | Service | Cost |
|-----------|---------|------|
| Hosting | Railway/Fly.io | ~$5-10/mo |
| Database | Railway Postgres | ~$5/mo |
| Email | Resend/Postmark | Free tier |
| Domain | auth.jimmypocock.com | Already have |

**Total: ~$10-15/month** vs Clerk's $25/month at scale

---

## Resources

- [JWT.io](https://jwt.io/) - JWT debugger
- [OWASP Auth Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OAuth 2.0 Simplified](https://aaronparecki.com/oauth-2-simplified/)
- [Lucia Auth](https://lucia-auth.com/) - Good reference implementation

---

## Notes

- Start with Greg's existing auth code as base
- Use RS256 (asymmetric) for JWTs so services can validate locally
- Keep it simple - add features as needed
- This replaces auth in ALL apps, so get it right
