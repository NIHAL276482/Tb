from flask import Flask, jsonify, request
from TeraboxDL import TeraboxDL
import os
import logging
from urllib.parse import urlparse
from http.cookiejar import MozillaCookieJar

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Supported Terabox domains
SUPPORTED_DOMAINS = [
    "terabox.com", "terabox.app", "terabox.me",
    "1024terabox.com", "teraboxd.com", "terabox.club"
]

# Load ndus cookie from Netscape-formatted cookies.txt
def load_ndus_cookie():
    if not os.path.exists("cookies.txt"):
        logger.error("cookies.txt not found")
        return None
    
    cookie_jar = MozillaCookieJar()
    try:
        cookie_jar.load("cookies.txt", ignore_discard=True, ignore_expires=True)
        for domain in SUPPORTED_DOMAINS:
            for cookie in cookie_jar:
                if cookie.name == "ndus" and domain in cookie.domain:
                    logger.info(f"Found ndus cookie for {cookie.domain}")
                    return f"lang=en; ndus={cookie.value}"
        logger.error("No ndus cookie found for any Terabox domain")
        return None
    except Exception as e:
        logger.error(f"Error reading cookies.txt: {e}")
        return None

# Validate Terabox URL
def is_valid_terabox_url(url):
    try:
        parsed = urlparse(url)
        is_valid = parsed.netloc and any(domain in parsed.netloc for domain in SUPPORTED_DOMAINS)
        logger.info(f"URL check: {url} - {'Valid' if is_valid else 'Invalid'}")
        return is_valid
    except Exception as e:
        logger.error(f"URL validation failed: {e}")
        return False

@app.route("/")
async def get_details():
    url = request.args.get("url")
    if not url:
        logger.error("No URL provided")
        return jsonify({"error": "No URL provided"}), 400

    if not is_valid_terabox_url(url):
        logger.error(f"Invalid Terabox URL: {url}")
        return jsonify({"error": "Invalid Terabox URL"}), 400

    # Load ndus cookie
    cookie = load_ndus_cookie()
    if not cookie:
        logger.error("No valid ndus cookie found")
        return jsonify({"error": "No valid ndus cookie found in cookies.txt"}), 400

    # Initialize TeraboxDL
    try:
        terabox = TeraboxDL(cookie)
        logger.info(f"TeraboxDL initialized for: {url}")
    except Exception as e:
        logger.error(f"TeraboxDL initialization failed: {e}")
        return jsonify({"error": f"TeraboxDL initialization failed: {str(e)}"}), 500

    # Fetch file details
    try:
        file_info = terabox.get_file_info(url)
        logger.info(f"Got file info: {file_info}")
        
        if "error" in file_info:
            logger.error(f"TeraboxDL error: {file_info['error']}")
            return jsonify({"error": f"Fetch failed: {file_info['error']}"}), 400

        # Extract and validate thumbnail
        tumbanail = file_info.get("thumbnail", "")
        if tumbanail:
            # Basic validation for thumbnail URL
            if not isinstance(tumbanail, str) or not tumbanail.startswith("https://"):
                logger.warning(f"Invalid thumbnail format: {tumbanail}, setting to null")
                tumbanail = None
        else:
            logger.info("No thumbnail available, setting to null")
            tumbanail = None

        # Extract and format response
        size_bytes = int(file_info.get("size_bytes", 0))
        response = {
            "bytes": size_bytes,
            "direct_link": file_info.get("download_link", ""),
            "tumbanail": tumbanail,
            "name": file_info.get("file_name", "unknown"),
            "Size": f"{round(size_bytes / (1024 * 1024), 2)} mb"
        }
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching file info: {e}")
        return jsonify({"error": f"Fetch error: {str(e)}"}), 500

# Suppress favicon requests
@app.route("/favicon.ico")
def favicon():
    return "", 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
