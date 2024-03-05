import requests
import urllib

BASE_URL = "http://3.101.106.167:8002" 

def make_request(endpoint, method='GET', data=None):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.request(method, url, json=data)
    return response

def read_file(filename):
    endpoint = f"read/{filename}"
    response = make_request(endpoint)
    if response.status_code == 200:
        return urllib.parse.unquote(response.json()["data"])
    else:
        return f"Failed to read file '{filename}': {response.text}"

def write_file(filename, content):
    content = urllib.parse.quote(content)
    # data = {"filename": filename, "content": content}
    endpoint = "write/{filename}/{content}"
    response = make_request(endpoint, method='GET')
    if response.status_code == 200:
        return f"File '{filename}' written successfully"
    else:
        return f"Failed to write to file '{filename}'"

def append_to_file(filename, content):
    endpoint = f"append/{filename}"
    data = {"content": content}
    response = make_request(endpoint, method='POST', data=data)
    if response.status_code == 200:
        return f"Content appended to file '{filename}' successfully"
    else:
        return f"Failed to append to file '{filename}'"

def delete_file(filename):
    endpoint = f"delete/{filename}"
    response = make_request(endpoint, method='DELETE')
    if response.status_code == 200:
        return f"File '{filename}' deleted successfully"
    else:
        return f"Failed to delete file '{filename}'"

def copy_file(src_filename, dest_filename):
    endpoint = f"copy/{src_filename}/{dest_filename}"
    response = make_request(endpoint, method='POST')
    if response.status_code == 200:
        return f"File '{src_filename}' copied to '{dest_filename}' successfully"
    else:
        return f"Failed to copy file '{src_filename}' to '{dest_filename}'"

def rename_file(old_filename, new_filename):
    endpoint = f"rename/{old_filename}/{new_filename}"
    response = make_request(endpoint, method='PUT')
    if response.status_code == 200:
        return f"File '{old_filename}' renamed to '{new_filename}' successfully"
    else:
        return f"Failed to rename file '{old_filename}' to '{new_filename}'"

def check_file_existence(filename):
    endpoint = f"exists/{filename}"
    response = make_request(endpoint)
    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        return f"Error checking if file '{filename}' exists: {response.text}"

# Test the functions
if __name__ == "__main__":
    try:
        # Test read
        print("Read: file1: ", read_file("file1.txt"))

        # Test write
        print(write_file("file4.txt", "This is file4.txt"))
        print("Read: file4: ", read_file("file4.txt"))

        # Test append
        print(append_to_file("file4.txt", " - Appended content"))
        print("Read: file4: ", read_file("file4.txt"))

        # Test delete
        print(delete_file("file4.txt"))

        # Test copy
        print(copy_file("file1.txt", "file5.txt"))
        print("Read: file5: ", read_file("file5.txt"))

        # Test rename
        print(rename_file("file5.txt", "file6.txt"))
        print("Read: file6: ", read_file("file6.txt"))

        # Test exists
        print("file1 Exists:", check_file_existence("file1.txt"))
        print("file6 Exists:", check_file_existence("file6.txt"))
        print("file5 Exists:", check_file_existence("file5.txt"))
    except Exception as e:
        print("Error:", e)