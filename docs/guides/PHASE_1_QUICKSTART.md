# Phase 1 Quick Start Guide

## 🚀 Getting Started with MFA Implementation

This guide helps you continue the Phase 1 implementation after Day 1's backend setup.

---

## ✅ What's Been Completed

### Backend (100% Day 1 Goals)
- ✅ Database models for MFA
- ✅ All 6 MFA API endpoints
- ✅ Dependencies installed
- ✅ Migration created and applied
- ✅ API routing configured

### Files Created/Modified

```
team_planner/users/
├── models.py (MODIFIED - added MFA models)
├── api/
│   └── mfa_views.py (NEW - MFA endpoints)
└── migrations/
    └── 0002_add_mfa_models.py (NEW)

config/
└── api_router.py (MODIFIED - added MFA routes)

requirements/
└── base.txt (MODIFIED - added pyotp, qrcode)
```

---

## 🔄 Next Steps - Frontend Implementation

### Step 1: Create MFA Setup Component

Create `frontend/src/components/auth/MFASetup.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Stepper,
  Step,
  StepLabel,
  Alert,
  Chip,
  Grid,
} from '@mui/material';
import { QrCode2, Security, VpnKey } from '@mui/icons-material';
import apiClient from '../../services/apiClient';

interface MFASetupProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const MFASetup: React.FC<MFASetupProps> = ({ open, onClose, onSuccess }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [verificationToken, setVerificationToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const steps = ['Scan QR Code', 'Verify Token', 'Save Backup Codes'];

  useEffect(() => {
    if (open) {
      initializeMFA();
    }
  }, [open]);

  const initializeMFA = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/api/mfa/setup/');
      setQrCode(response.data.qr_code);
      setSecret(response.data.secret);
      setBackupCodes(response.data.backup_codes);
      setActiveStep(0);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to initialize MFA');
    } finally {
      setLoading(false);
    }
  };

  const verifyToken = async () => {
    setLoading(true);
    setError('');
    try {
      await apiClient.post('/api/mfa/verify/', {
        token: verificationToken,
      });
      setActiveStep(2);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Invalid token');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = () => {
    onSuccess();
    onClose();
  };

  const handleNext = () => {
    if (activeStep === 0) {
      setActiveStep(1);
    } else if (activeStep === 1) {
      verifyToken();
    } else {
      handleComplete();
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const downloadBackupCodes = () => {
    const element = document.createElement('a');
    const file = new Blob([backupCodes.join('\n')], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = 'team-planner-backup-codes.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Security color="primary" />
          Enable Two-Factor Authentication
        </Box>
      </DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Step 1: QR Code */}
        {activeStep === 0 && (
          <Box textAlign="center">
            <Typography variant="body1" gutterBottom>
              Scan this QR code with your authenticator app
            </Typography>
            <Typography variant="caption" display="block" gutterBottom>
              (Google Authenticator, Authy, Microsoft Authenticator, etc.)
            </Typography>
            {qrCode && (
              <Box my={2}>
                <img src={qrCode} alt="MFA QR Code" style={{ maxWidth: '300px' }} />
              </Box>
            )}
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Or enter this key manually:
            </Typography>
            <Box display="flex" alignItems="center" justifyContent="center" gap={1}>
              <Chip 
                label={secret} 
                onClick={() => copyToClipboard(secret)}
                icon={<VpnKey />}
              />
              <Button size="small" onClick={() => copyToClipboard(secret)}>
                Copy
              </Button>
            </Box>
          </Box>
        )}

        {/* Step 2: Verify */}
        {activeStep === 1 && (
          <Box>
            <Typography variant="body1" gutterBottom>
              Enter the 6-digit code from your authenticator app
            </Typography>
            <TextField
              fullWidth
              label="Verification Code"
              value={verificationToken}
              onChange={(e) => setVerificationToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              inputProps={{ 
                maxLength: 6, 
                style: { fontSize: '24px', textAlign: 'center', letterSpacing: '8px' } 
              }}
              sx={{ my: 2 }}
            />
          </Box>
        )}

        {/* Step 3: Backup Codes */}
        {activeStep === 2 && (
          <Box>
            <Alert severity="warning" sx={{ mb: 2 }}>
              <strong>Important!</strong> Save these backup codes in a secure place. 
              You can use them to access your account if you lose your authenticator device.
            </Alert>
            <Grid container spacing={1}>
              {backupCodes.map((code, index) => (
                <Grid item xs={6} key={index}>
                  <Chip 
                    label={code} 
                    sx={{ 
                      fontFamily: 'monospace', 
                      width: '100%',
                      fontSize: '14px'
                    }}
                  />
                </Grid>
              ))}
            </Grid>
            <Box mt={2} display="flex" gap={1}>
              <Button
                variant="outlined"
                onClick={() => copyToClipboard(backupCodes.join('\n'))}
                fullWidth
              >
                Copy All
              </Button>
              <Button
                variant="outlined"
                onClick={downloadBackupCodes}
                fullWidth
              >
                Download
              </Button>
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={loading || (activeStep === 1 && verificationToken.length !== 6)}
        >
          {loading ? 'Processing...' : (activeStep === 2 ? 'Finish' : 'Next')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MFASetup;
```

### Step 2: Test the API Endpoints

You can test the backend with curl:

```bash
# 1. Get auth token first
TOKEN="your-auth-token-here"

# 2. Initialize MFA setup
curl -X POST http://localhost:8000/api/mfa/setup/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json"

# 3. Verify with a token
curl -X POST http://localhost:8000/api/mfa/verify/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token": "123456"}'

# 4. Check MFA status
curl -X GET http://localhost:8000/api/mfa/status/ \
  -H "Authorization: Token $TOKEN"
```

---

## 🧪 Testing Guide

### Manual Testing Checklist

1. **Setup Flow**
   - [ ] User can initiate MFA setup
   - [ ] QR code displays correctly
   - [ ] Secret key can be copied
   - [ ] Backup codes are generated

2. **Verification Flow**
   - [ ] Valid token is accepted
   - [ ] Invalid token is rejected
   - [ ] Token window works (30s drift)
   - [ ] Backup codes displayed after verification

3. **Login Flow**
   - [ ] Login requires MFA token after password
   - [ ] Valid token grants access
   - [ ] Backup codes work
   - [ ] Failed attempts are logged

4. **Disable Flow**
   - [ ] Password required
   - [ ] Token required
   - [ ] Device removed after disable
   - [ ] Can re-enable MFA

### Unit Tests to Write

Create `team_planner/users/tests/test_mfa.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from team_planner.users.models import TwoFactorDevice, MFALoginAttempt

User = get_user_model()


@pytest.mark.django_db
class TestTwoFactorDevice:
    def test_generate_secret(self):
        """Test secret key generation."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        secret = device.generate_secret()
        
        assert len(secret) == 32
        assert secret.isalnum()
        assert secret.isupper()
    
    def test_verify_token(self):
        """Test TOTP token verification."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        device.generate_secret()
        
        # Get current token
        totp = device.get_totp()
        token = totp.now()
        
        # Should verify successfully
        assert device.verify_token(token) is True
    
    def test_backup_codes(self):
        """Test backup code generation and verification."""
        user = User.objects.create_user(username='test', email='test@example.com')
        device = TwoFactorDevice.objects.create(user=user)
        codes = device.generate_backup_codes(count=10)
        
        assert len(codes) == 10
        assert all(len(code) == 8 for code in codes)
        
        # Verify a code
        code = codes[0]
        assert device.verify_backup_code(code) is True
        
        # Code should be removed after use
        assert code not in device.backup_codes
        
        # Can't use same code twice
        assert device.verify_backup_code(code) is False
```

---

## 📖 API Documentation

### POST /api/mfa/setup/

**Description:** Initialize MFA setup for current user

**Headers:**
```
Authorization: Token <auth-token>
Content-Type: application/json
```

**Response 200:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,...",
  "backup_codes": [
    "A1B2C3D4",
    "E5F6G7H8",
    ...
  ],
  "is_verified": false
}
```

### POST /api/mfa/verify/

**Description:** Verify MFA setup with TOTP token

**Headers:**
```
Authorization: Token <auth-token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "123456"
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "MFA verified successfully",
  "backup_codes": ["A1B2C3D4", "E5F6G7H8", ...]
}
```

**Response 400:**
```json
{
  "error": "Invalid token"
}
```

### GET /api/mfa/status/

**Description:** Get MFA status for current user

**Headers:**
```
Authorization: Token <auth-token>
```

**Response 200 (Enabled):**
```json
{
  "enabled": true,
  "verified": true,
  "device_name": "Authenticator App",
  "last_used": "2025-10-01T10:30:00Z",
  "backup_codes_remaining": 8
}
```

**Response 200 (Not Enabled):**
```json
{
  "enabled": false,
  "verified": false
}
```

---

## 🔒 Security Best Practices

### For Development

1. **Never commit secrets** - Use environment variables
2. **Test with real authenticator apps** - Google Authenticator, Authy
3. **Verify backup codes work** - Critical fallback mechanism
4. **Test clock drift** - Ensure 30s window works
5. **Check logging** - Verify MFALoginAttempt records created

### For Production

1. **Enforce MFA for staff** - Set `mfa_required=True` for admin users
2. **Monitor failed attempts** - Alert on multiple failures
3. **Rate limit endpoints** - Prevent brute force attacks
4. **Use HTTPS only** - Never transmit tokens over HTTP
5. **Regular backup code audits** - Ensure users have codes saved

---

## 🐛 Troubleshooting

### QR Code Not Displaying

**Problem:** QR code returns empty or error

**Solution:**
1. Check `pyotp` is installed: `pip show pyotp`
2. Check `qrcode[pil]` is installed: `pip show qrcode pillow`
3. Verify secret key is generated: Check database

### Token Always Invalid

**Problem:** Valid tokens are rejected

**Possible Causes:**
1. Clock drift > 30 seconds
2. Wrong secret key
3. Device not saved to database

**Solution:**
1. Check server time: `date`
2. Check mobile device time
3. Verify secret in database matches QR code

### Migration Errors

**Problem:** Migration fails to apply

**Solution:**
```bash
# Reset migrations (development only!)
python3 manage.py migrate users zero
python3 manage.py migrate users
```

---

## 📞 Need Help?

- Review the full implementation plan: `PHASE_1_IMPLEMENTATION_PLAN.md`
- Check progress tracking: `PHASE_1_PROGRESS.md`
- Backend code: `team_planner/users/api/mfa_views.py`
- Models: `team_planner/users/models.py`

---

**Last Updated:** October 1, 2025  
**Next Update:** Day 2 - Frontend Components
