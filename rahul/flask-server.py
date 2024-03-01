from flask import Flask, request, jsonify
import os
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Route for writing to a file
@app.route('/write', methods=['POST'])
def write_file():
    data = request.get_json()
    if data and 'filename' in data and 'content' in data:
        filename = data['filename']
        content = data['content']
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'w') as file:
            file.write(content)
        return jsonify({"message": f"File '{filename}' written successfully"})
    else:
        return jsonify({"error": "Invalid request format"}), 400

# Route for reading a file
@app.route('/read/<filename>', methods=['GET'])
def read_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            content = file.read()
        return jsonify({"content": content})
    else:
        return jsonify({"error": "File not found"}), 404

# Route for appending to a file
@app.route('/append/<filename>', methods=['POST'])
def append_file(filename):
    data = request.get_json()
    if data and 'content' in data:
        content = data['content']
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'a') as file:
            file.write(content)
        return jsonify({"message": f"Content appended to file '{filename}' successfully"})
    else:
        return jsonify({"error": "Invalid request format"}), 400

# Route for deleting a file
@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"message": f"File '{filename}' deleted successfully"})
    else:
        return jsonify({"error": "File not found"}), 404

# Route for copying a file
@app.route('/copy/<src_filename>/<dest_filename>', methods=['POST'])
def copy_file(src_filename, dest_filename):
    src_filepath = os.path.join(UPLOAD_FOLDER, src_filename)
    dest_filepath = os.path.join(UPLOAD_FOLDER, dest_filename)
    if os.path.exists(src_filepath):
        shutil.copy(src_filepath, dest_filepath)
        return jsonify({"message": f"File '{src_filename}' copied to '{dest_filename}' successfully"})
    else:
        return jsonify({"error": "Source file not found"}), 404

# Route for renaming a file
@app.route('/rename/<old_filename>/<new_filename>', methods=['PUT'])
def rename_file(old_filename, new_filename):
    old_filepath = os.path.join(UPLOAD_FOLDER, old_filename)
    new_filepath = os.path.join(UPLOAD_FOLDER, new_filename)
    if os.path.exists(old_filepath):
        os.rename(old_filepath, new_filepath)
        return jsonify({"message": f"File '{old_filename}' renamed to '{new_filename}' successfully"})
    else:
        return jsonify({"error": "File not found"}), 404

# Route for checking if a file exists
@app.route('/exists/<filename>', methods=['GET'])
def check_file_existence(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return jsonify({"exists": True})
    else:
        return jsonify({"exists": False})

if __name__ == '__main__':
    app.run(port=5000, debug=True)

