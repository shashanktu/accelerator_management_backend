from sample import app

# Vercel serverless function handler
def handler(request, response):
    return app(request, response)