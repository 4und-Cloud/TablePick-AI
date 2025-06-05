from pathlib import Path

def get_project_root() -> Path:
    """
    프로젝트 루트 경로(Path 객체)를 반환합니다.
    (이 함수 파일이 src/utils/에 있다고 가정)
    """
    return Path(__file__).resolve().parent.parent.parent

def get_data_path(*subpaths, mkdir=False) -> Path:
    """
    프로젝트 루트 기준 data/ 하위 경로를 반환합니다.
    subpaths: data/ 아래의 하위 디렉토리 및 파일명 (가변 인자)
    mkdir: True면 디렉토리 자동 생성
    """
    root = get_project_root()
    full_path = root.joinpath('data', *subpaths)
    if mkdir:
        # 파일이 아니라 디렉토리 경로만 생성
        dir_path = full_path if full_path.suffix == '' else full_path.parent
        dir_path.mkdir(parents=True, exist_ok=True)
    return full_path
