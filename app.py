from flask import Flask, request, render_template, send_file
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

app = Flask(__name__, template_folder="templates")

DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)


# GET USER KEY FILE
def get_user_key_path(user_id):
    return os.path.join(DATA_FOLDER, f"{user_id}_aes.key")


# HOME PAGE
@app.route("/")
def index():
    files = [f.replace(".enc", "") for f in os.listdir(DATA_FOLDER) if f.endswith(".enc")]
    return render_template("index.html", files=files)


# REGISTER USER → GENERATE AES-256 KEY
@app.route("/register", methods=["POST"])
def register():
    user_id = request.form.get("user_id")

    if not user_id:
        return "User ID required", 400

    key_path = get_user_key_path(user_id)

    if os.path.exists(key_path):
        return f"User '{user_id}' already registered."

    key = get_random_bytes(32)  # AES-256 KEY

    with open(key_path, "wb"):
        pass

    with open(key_path, "wb") as f:
        f.write(key)

    return f"User '{user_id}' registered! AES key generated."


# UPLOAD + ENCRYPT FILE
@app.route("/upload", methods=["POST"])
def upload():
    user_id = request.form.get("user_id")
    file = request.files.get("file")

    if not user_id or not file:
        return "User ID and File required!", 400

    key_path = get_user_key_path(user_id)
    if not os.path.exists(key_path):
        return f"User '{user_id}' not registered."

    # Load AES key
    with open(key_path, "rb") as f:
        aes_key = f.read()

    original = file.filename
    temp_path = os.path.join(DATA_FOLDER, original)
    file.save(temp_path)

    # AES Encrypt
    cipher = AES.new(aes_key, AES.MODE_EAX)

    with open(temp_path, "rb") as f:
        data = f.read()

    ciphertext, tag = cipher.encrypt_and_digest(data)

    enc_path = os.path.join(DATA_FOLDER, original + ".enc")

    # FILE FORMAT → NONCE | TAG | CIPHERTEXT
    with open(enc_path, "wb") as f:
        f.write(cipher.nonce)
        f.write(tag)
        f.write(ciphertext)

    os.remove(temp_path)

    return f"File '{original}' encrypted successfully!"


# DOWNLOAD + DECRYPT
@app.route("/download", methods=["POST"])
def download():
    user_id = request.form.get("user_id")
    filename = request.form.get("filename")

    if not user_id or not filename:
        return "User ID and filename required!", 400

    key_path = get_user_key_path(user_id)
    enc_path = os.path.join(DATA_FOLDER, filename + ".enc")

    if not os.path.exists(key_path):
        return "User not registered!", 404

    if not os.path.exists(enc_path):
        return "Encrypted file not found!", 404

    # Read AES key
    with open(key_path, "rb") as f:
        aes_key = f.read()

    # Read encrypted structure
    with open(enc_path, "rb") as f:
        nonce = f.read(16)
        tag = f.read(16)
        ciphertext = f.read()

    # AES Decrypt
    cipher = AES.new(aes_key, AES.MODE_EAX, nonce=nonce)

    try:
        decrypted = cipher.decrypt_and_verify(ciphertext, tag)
    except:
        return "Wrong key! Cannot decrypt.", 400

    out_name = f"DECRYPTED_{filename}"
    out_path = os.path.join(DATA_FOLDER, out_name)

    with open(out_path, "wb") as f:
        f.write(decrypted)

    # Send file
    response = send_file(out_path, as_attachment=True)

    @response.call_on_close
    def cleanup():
        os.remove(out_path)

    return response


# RUN APP
if __name__ == "__main__":
    app.run(debug=True)

# END OF FILE