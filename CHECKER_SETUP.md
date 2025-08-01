# Document Checker Setup Guide

## Overview
The document checker integrates with GovDocVerify to validate documents for headings, accessibility, and FAA style compliance. The checker was previously showing demo content due to configuration issues.

## Issues Fixed

### 1. Demo Content Removal
- ✅ Removed `DEMO_RESULT` fallback that was showing fake data
- ✅ Added proper error handling and user feedback
- ✅ Added API connection status indicator

### 2. API Configuration
- ✅ Improved error handling in the API endpoint
- ✅ Added comprehensive logging for debugging
- ✅ Better error messages for troubleshooting

## Setup Requirements

### 1. Environment Variables
Create a `.env.local` file in the `frontend/` directory:

```bash
# Backend API base URL (required)
NEXT_PUBLIC_API_BASE=http://localhost:8000

# Python environment (optional)
VENV_PYTHON=/path/to/your/python/executable
```

### 2. Backend Server
Ensure the backend server is running:

```bash
# From the project root
cd DocReview360
python -m uvicorn docreview360.api:app --host 0.0.0.0 --port 8000
```

### 3. GovDocVerify Installation
The system automatically installs GovDocVerify from the Git repository. Verify installation:

```bash
python -c "import govdocverify; print('GovDocVerify installed successfully')"
```

## Troubleshooting

### Common Issues

1. **"Backend connection failed"**
   - Ensure backend server is running on port 8000
   - Check `NEXT_PUBLIC_API_BASE` environment variable
   - Verify network connectivity

2. **"Python execution failed"**
   - Check Python installation and PATH
   - Verify GovDocVerify is installed
   - Check file permissions for uploaded documents

3. **"Failed to parse JSON output"**
   - GovDocVerify may not be returning valid JSON
   - Check Python module installation
   - Review server logs for detailed error information

### Debug Steps

1. **Check Browser Console**
   - Open Developer Tools (F12)
   - Look for network errors and API responses
   - Check for JavaScript errors

2. **Check Server Logs**
   - Monitor backend server console output
   - Look for Python execution errors
   - Check file upload and processing logs

3. **Test GovDocVerify Directly**
   ```bash
   python -m docreview360.document_checker /path/to/test.docx
   ```

## Expected Behavior

When working correctly, the checker should:

1. ✅ Show "Connected to GovDocVerify backend" status
2. ✅ Process uploaded DOC/DOCX files
3. ✅ Display actual GovDocVerify results (not demo content)
4. ✅ Show detailed validation results including:
   - Grammar issues
   - Accessibility problems
   - Style compliance
   - Document structure issues

## File Structure

```
DocReview360/
├── frontend/
│   ├── pages/
│   │   ├── tools/
│   │   │   └── checker.tsx          # Main checker UI
│   │   └── api/
│   │       └── tools/
│   │           └── checker.ts       # API endpoint
│   └── lib/
│       └── api.ts                   # API configuration
└── src/
    └── docreview360/
        └── document_checker.py      # GovDocVerify integration
```

## Testing

1. Upload a test DOCX file
2. Check browser console for API calls
3. Verify results show actual GovDocVerify output
4. Confirm no demo content appears

## Support

If issues persist:
1. Check the troubleshooting section above
2. Review server logs for detailed error messages
3. Verify GovDocVerify installation and configuration
4. Test with a simple document first
