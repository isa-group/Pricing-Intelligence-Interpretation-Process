import os

from harvey_api.file_manager import FileManager


def test_create_file(tmp_path):

    file_manager = FileManager(tmp_path)
    filename = "test.txt"
    content = b"Test content"
    file_manager.write_file(filename, content)

    assert os.path.exists(tmp_path / filename)

def test_delete_file(tmp_path):

    file_manager = FileManager(tmp_path)
    filename = "test.txt"
    content = b"Test content"
    file_manager.write_file(filename, content)
    assert os.path.exists(tmp_path / filename)
    
    file_manager.delete_file(filename)
    assert not os.path.exists(tmp_path / filename)