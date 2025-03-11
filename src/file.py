class FileMemory:
    files = {}

    def __init__(self):
        self.files = {}

    def add_file(self, file_id, file):
        file["progress"] = 0
        file["status"] = "pending"
        self.files[file_id] = file
        

    def update_progress(self, file_id, progress):
        self.files[file_id]["progress"] = progress

    def get_file(self, file_id):
        return self.files.get(file_id)
    
    def set_file_completed(self, file_id):
        self.files[file_id]["status"] = "completed"
        

    
