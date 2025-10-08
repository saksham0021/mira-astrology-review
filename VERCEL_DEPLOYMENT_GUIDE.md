# Vercel Deployment Guide for Mira Astrology Review System

## Pre-Deployment Checklist ✅

### 1. Files Created/Updated
- ✅ `vercel.json` - Vercel configuration
- ✅ `api/index.py` - Vercel entry point
- ✅ `runtime.txt` - Python version specification
- ✅ `.env.example` - Environment variables template
- ✅ Updated `requirements.txt` with production dependencies
- ✅ Updated `.gitignore` to allow vercel.json

### 2. Google Sheets Setup
- ✅ `credentials.json` file exists in `credentials.json/` directory
- ✅ Google Sheets URL configured in app
- ✅ Service account has access to the spreadsheet

### 3. Database
- ✅ SQLite database initialization handled in code
- ✅ Database schema creation automated
- ✅ All required tables and indexes created

## Deployment Steps

### Step 1: Prepare for Deployment
1. Ensure all files are committed to your Git repository
2. Make sure `credentials.json` is in the correct location
3. Test the application locally one final time

### Step 2: Deploy to Vercel
1. Install Vercel CLI: `npm install -g vercel`
2. Login to Vercel: `vercel login`
3. Deploy: `vercel --prod`

### Step 3: Configure Environment Variables
In Vercel dashboard, add these environment variables:
- `SECRET_KEY`: Generate a secure random key
- `GOOGLE_SHEETS_URL`: Your Google Sheets URL
- `GOOGLE_CREDENTIALS_FILE`: `credentials.json/credentials.json`
- `FLASK_ENV`: `production`

### Step 4: Upload Credentials
Upload your `credentials.json` file to Vercel:
1. Go to your project settings in Vercel
2. Navigate to "Functions" tab
3. Upload the credentials file

## Important Notes

### Database Considerations
- Currently using SQLite (file-based database)
- For production, consider upgrading to PostgreSQL or MySQL
- Vercel has limitations with file persistence

### Google Sheets Integration
- Ensure service account has proper permissions
- Test the connection after deployment
- Monitor API quotas and limits

### Security
- All sensitive data should be in environment variables
- HTTPS is enforced in production
- Security headers are automatically added

## Testing After Deployment

1. **Basic Functionality**
   - Visit your Vercel URL
   - Check if the main page loads
   - Test session loading

2. **Google Sheets Sync**
   - Test the "Refresh Data" button
   - Submit a test review
   - Verify bidirectional sync works

3. **Astrologer Workflow**
   - Load a session
   - Submit markings/reviews
   - Check if data persists

## Troubleshooting

### Common Issues
1. **Import Errors**: Check if all dependencies are in requirements.txt
2. **Database Errors**: Ensure init_db() runs successfully
3. **Google Sheets Errors**: Verify credentials and permissions
4. **Timeout Errors**: Consider optimizing database queries

### Logs
- Check Vercel function logs in the dashboard
- Monitor performance and errors
- Set up alerts for critical issues

## Post-Deployment
- Share the Vercel URL with astrologers
- Monitor usage and performance
- Set up regular backups if using file-based database
- Consider upgrading to a managed database service

## Support
If you encounter issues:
1. Check Vercel function logs
2. Test Google Sheets connection
3. Verify all environment variables are set
4. Ensure credentials file is properly uploaded
