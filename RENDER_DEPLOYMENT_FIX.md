# How to Fix the Cleanup Error on Render

## The Problem

You're seeing this error in your Render logs:
```
ERROR - Error in cleanup process: 'NoneType' object is not subscriptable
```

And this warning:
```
WARNING: This is a development server. Do not use it in a production deployment.
```

## The Solution

I've fixed both issues! Follow these steps to deploy the fixes:

---

## Step 1: Update Your Code

The code has been fixed with the following changes:

1. **Fixed cleanup process error** - Added proper null checks in `message_manager.py`
2. **Added production server** - Added Gunicorn for production deployment
3. **Created WSGI entry point** - New `wsgi.py` file for production

---

## Step 2: Push Changes to GitHub

```bash
git add .
git commit -m "Fix cleanup error and add production server"
git push origin main
```

---

## Step 3: Update Render Configuration

### Option A: Update via render.yaml (Automatic)

The `render.yaml` file has been updated automatically. Render will use it on next deployment.

### Option B: Update via Render Dashboard (Manual)

If Render doesn't pick up the yaml changes:

1. Go to your **Render Dashboard**
2. Click on your **telegram-video-bot** service
3. Click **Settings**
4. Scroll to **Build & Deploy**
5. Update **Start Command** to:
   ```
   gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT --timeout 120
   ```
6. Click **Save Changes**

---

## Step 4: Deploy

In your Render dashboard:

1. Click **Manual Deploy**
2. Select **Deploy latest commit**
3. Wait for deployment to complete (2-3 minutes)

---

## Step 5: Verify the Fix

Check your Render logs. You should see:

✅ **No more "NoneType" errors** in cleanup process  
✅ **No more development server warning**  
✅ **Gunicorn running with 2 workers**  
✅ Messages like: `[INFO] Starting gunicorn`

---

## What Was Fixed?

### 1. Cleanup Error Fix
- Added null/None checks before accessing message data
- Added validation for required fields (delete_at, user_id, message_id)
- Better error handling with detailed logging

### 2. Production Server
- Added Gunicorn (production WSGI server)
- Configured 2 workers for better performance
- 120-second timeout for long-running requests

---

## Using Supabase Database (Next Step)

After fixing these errors, you can migrate to Supabase:

1. Create a Supabase project
2. Get your connection string
3. Update `DATABASE_URL` in Render environment variables
4. Redeploy

This will replace Render's 30-day expiring database with Supabase's permanent free tier!

---

## Need Help?

If you still see errors after deployment:

1. Check Render logs for the specific error message
2. Make sure all environment variables are set (BOT_TOKEN, PRIVATE_CHANNEL_ID, PUBLIC_CHANNEL_ID)
3. Verify your bot is admin in both Telegram channels

---

## Summary

✅ Cleanup error fixed - no more NoneType issues  
✅ Production server added - no more development warnings  
✅ Ready to deploy with `git push` + Render deploy  
