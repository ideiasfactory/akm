import toml
from src.api.models.akm_project_info import AkmProjectInfo

def get_project_info():
  # Read pyproject.toml
  with open("pyproject.toml", "r") as f:
    pyproject = toml.load(f)

  project = pyproject.get("project", {})
  
  return AkmProjectInfo(
      name=project.get("name"),
      version=project.get("version"),
      description=project.get("description"),
      requires_python=project.get("requires-python"),
      docs_url=project.get("url")
  )
