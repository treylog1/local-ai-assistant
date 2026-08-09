import pathlib as pl
from pathlib import Path

class FileTools:
    def __init__(self):
        self.tools = {
            "making_file": self.making_file,
            "reading_file": self.reading_file,
            "writing_file": self.writing_file,
            "deleting_file": self.deleting_file,
            "renaming_file": self.renaming_file
        }

        
    def making_file(self, file_name, file_location):
        try:
            Path(file_location).joinpath(file_name).touch()
            return {"status": "success", "message": f"File '{file_name}' created in '{file_location}'."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reading_file(self, file_name, file_location):
        try:
            with open(Path(file_location).joinpath(file_name), "r") as file:
                content = file.read()
            return {"status": "success", "content": content}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def writing_file(self, file_name, file_location, content):
        try:
            with open(Path(file_location).joinpath(file_name), "w") as file:
                file.write(content)
            return {"status": "success", "message": f"Content written to '{file_name}' in '{file_location}'."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def deleting_file(self, file_name, file_location):
        try:
            Path(file_location).joinpath(file_name).unlink()
            return {"status": "success", "message": f"File '{file_name}' deleted from '{file_location}'."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    def renaming_file(self, file_name, new_file_name, file_location):
        try:
            Path(file_location).joinpath(file_name).rename(Path(file_location).joinpath(new_file_name))
            return {"status": "success", "message": f"Renamed '{file_name}' to '{new_file_name}' in '{file_location}'."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
   