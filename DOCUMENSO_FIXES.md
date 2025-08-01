# Documenso Signature Integration Fixes

## Issues Identified and Fixed

### 1. **API Endpoint Mismatch**
- **Problem**: Frontend was calling `/sign/${sig}/complete` but backend expected `/api/sign/${sig}/complete`
- **Fix**: Updated frontend to use proper API base URL with `${API}/sign/${sig}/complete`

### 2. **Missing Error Handling**
- **Problem**: No proper error handling for failed signature requests
- **Fix**: Added comprehensive error handling with user-friendly messages and console logging

### 3. **Incomplete State Management**
- **Problem**: Approval state wasn't being properly updated after signature completion
- **Fix**: Added localStorage synchronization and backend state updates

### 4. **Missing API Headers**
- **Problem**: API calls were missing proper Content-Type headers
- **Fix**: Added proper headers to all API requests

### 5. **Inconsistent Return URL Handling**
- **Problem**: Return URLs weren't properly encoded and didn't include approval context
- **Fix**: Added proper URL encoding and approval ID parameters

## Files Modified

### 1. `frontend/pages/projects/[id]/index.tsx`
- Enhanced `signApproval()` function with better error handling
- Added debugging logs for troubleshooting
- Added signature completion state synchronization
- Added `syncApprovalWithBackend()` function
- Added useEffect to check for completed signatures on page load

### 2. `frontend/pages/documenso/[sig].tsx`
- Fixed API endpoint calls to use proper base URL
- Added comprehensive error handling and user feedback
- Added immediate backend synchronization after signature completion
- Added debugging logs for troubleshooting
- Improved return URL handling

## How the Fixed Flow Works

1. **User clicks "Sign & Approve"**:
   - Frontend calls `${API}/approvals/${aid}/sign`
   - Backend creates signature request and returns signature ID and URL
   - Frontend redirects to Documenso with proper parameters

2. **User completes signature on Documenso page**:
   - Frontend calls `${API}/sign/${sig}/complete`
   - Backend marks signature as completed
   - Frontend stores completion timestamp in localStorage
   - Frontend immediately syncs approval state with backend
   - User is redirected back to project page

3. **User returns to project page**:
   - Frontend checks localStorage for completed signatures
   - Updates approval state to show as "approved" with timestamp
   - Syncs any missing state with backend

## Troubleshooting

### Check Browser Console
The fixes include comprehensive console logging. Check the browser console for:
- Signature request responses
- Completion responses
- Backend sync responses
- Any error messages

### Common Issues

1. **API Base URL Not Set**:
   - Ensure `NEXT_PUBLIC_API_BASE` environment variable is set
   - Check `frontend/lib/api.ts` for proper configuration

2. **Backend Not Running**:
   - Ensure the DocReview360 backend is running
   - Check that the API endpoints are accessible

3. **Documenso Service Not Available**:
   - If using external Documenso, ensure `DOCUMENSO_URL` is set
   - If using local stub, ensure backend is running

### Testing the Fix

1. Navigate to a project with pending approvals
2. Click "Sign & Approve" on an approval row
3. Complete the signature on the Documenso page
4. Verify you're redirected back to the project page
5. Check that the approval shows as "approved" with timestamp
6. Verify the approval state persists after page refresh

## Environment Variables Required

```bash
# Frontend
NEXT_PUBLIC_API_BASE=http://localhost:8000

# Backend (optional - for external Documenso)
DOCUMENSO_URL=https://your-documenso-instance.com
```

## API Endpoints Used

- `POST /approvals/{approval_id}/sign` - Start signature process
- `POST /sign/{sig_id}/complete` - Complete signature
- `PUT /approvals/{approval_id}` - Update approval state
- `GET /approvals?workflow={workflow_id}` - Get approvals for workflow
