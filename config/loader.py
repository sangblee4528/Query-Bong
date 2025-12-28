import os
import json

def load_config():
    """로드된 설정 정보를 담은 딕셔너리를 반환하며, 경로들을 절대 경로로 변환합니다."""
    # config/loader.py의 위치를 기준으로 프로젝트 루트 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    config_path = os.path.join(current_dir, "config.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # 설정 기반 절대 경로 계산
    config['PROJECT_ROOT'] = project_root
    config['DB_PATH'] = os.path.join(project_root, config['database']['path'])
    config['GEN_DB_PATH'] = os.path.join(project_root, config['database']['generated_path'])
    config['CATALOG_PATH'] = os.path.join(project_root, config['catalog']['output_path'])
    config['TEMPLATES_PATH'] = os.path.join(project_root, config['templates']['path'])
    config['SOURCE_PATH'] = os.path.join(project_root, config['source']['path'])
    
    return config

# 전역 설정 객체
CFG = load_config()
