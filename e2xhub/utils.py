import os
import yaml
from pathlib import Path
import pandas as pd


def load_yaml(yaml_file):
    """
    Load yaml file
    args:
        yaml_file: yaml file to load
    """
    configs = {}
    with open(yaml_file, 'r') as infile:
        configs = yaml.safe_load(infile)
    return configs

def get_directory(server_cfg, directory_key):
    """
    Get directory path given config and directory key.
    Return the value if the dir exists otherwise None
    args:
        config: configuration
        directory_key: the key in the config that contains the dir path to check
    """
    if check_consecutive_keys(server_cfg, directory_key):
        grader_user_dir = server_cfg[directory_key]
        if os.path.isdir(grader_user_dir):
            grader_user_dir = grader_user_dir
            return grader_user_dir
    return None

def load_server_cfg(config_file, server_name):
    """
    Load server config given server_name
    args:
        config_file: yaml file to load
        server_name: name of the server
    """
    if os.path.isfile(config_file):
        configs = load_yaml(config_file)
        if configs:
            if check_consecutive_keys(configs, "server", server_name):
                server_cfg = configs["server"][server_name]
                return server_cfg
    return None

def get_allowed_graders(server_cfg, grader_user_dir):
    """
    Get allowed graders given a list of courses in the server config
    args:
        server_cfg: server configuration
        grader_user_dir: path to the directory where the list of graders is located
    """
    allowed_graders = {}
    grader_course_cfg = []
    if check_consecutive_keys(server_cfg, "nbgrader", 
                            "formgrader", "grader_course_cfg"):

        grader_course_cfg = server_cfg['nbgrader']['formgrader']['grader_course_cfg']
        allowed_graders = get_allowed_users(grader_user_dir, grader_course_cfg)
        
    return allowed_graders, grader_course_cfg

def get_allowed_students(server_cfg, student_user_dir):
    """
    Get allowed students given a list of courses in the server config
    args:
        server_cfg: server configuration
        student_user_dir: path to the directory where the list of students is located
    """
    allowed_students = {}
    student_course_cfg = {}
    if check_consecutive_keys(server_cfg, "nbgrader", 
                            "student_course_cfg"):
        student_course_cfg = server_cfg['nbgrader']['student_course_cfg']
        allowed_students = get_allowed_users(student_user_dir, student_course_cfg)
        
    return allowed_students, student_course_cfg

def get_jupyterhub_users(server_cfg):
    """
    Get JupyterHub users (allowed_users, blocked_users, and admin_users)
    args:
        server_cfg: server configuration
    """
    jupyterhub_users = {'allowed_users': [],
                        'blocked_users': [],
                        'admin_users': []}
    if "user_list_path" not in server_cfg:
        return jupyterhub_users
        
    user_list_path = Path(server_cfg["user_list_path"])
    user_list_file_path = [item for item in user_list_path.iterdir() 
                           if item.is_file() and not item.name.startswith('.')
                           and ".csv" in item.name.lower()]
    for user_file_path in user_list_file_path:
        if "admin" in user_file_path.name.lower():
            jupyterhub_users['admin_users'].extend(list(pd.read_csv(user_file_path).Username.str.strip()))
        elif "allowed_users" in user_file_path.name.lower():
            jupyterhub_users['allowed_users'].extend(list(pd.read_csv(user_file_path).Username.str.strip()))
        elif "blocked_users" in user_file_path.name.lower():
            jupyterhub_users['blocked_users'].extend(list(pd.read_csv(user_file_path).Username.str.strip()))
    
    return jupyterhub_users
                    
def check_consecutive_keys(config, *argv):
    """
    Check consecutive keys given config
    args:
        config: server configuration
    """
    for key in argv:
        if key in config:
            config = config[key]
        else:
            return False
    return True

def get_nbgrader_cfg(server_cfg):
    """
    Get nbgrader grader config
    args:
        server_cfg: server configuration
    """
    nbgrader_cfg = {}
    if check_consecutive_keys(server_cfg, "nbgrader"):
        nbgrader_cfg = server_cfg['nbgrader']

    return nbgrader_cfg

def configure_volume_mount(volume_name,
                           volume_mountpath, 
                           volume_subpath,
                           read_only=False):
    """
    Configure volume mount in according to k8s specs
    args:
        volume_name: the name of the available volume
        volume_mountpath: the path to which the volume is mounted in the container
        volume_subpath: the subpath of the volume on the virtual or physical disk
        read_only: permission of the volume
    """
    volume_mount = {}       
    volume_mount['name'] = volume_name
    volume_mount['mountPath'] = volume_mountpath
    volume_mount['subPath'] = volume_subpath
    volume_mount['readOnly'] = read_only
    
    return volume_mount

def get_allowed_users(path, course_list):
    """
    Get allowed users given course list
    args:
        path: a path to the course list
        course_list: a list of the courses 
    """
    course_members = {}
    for course_name in course_list:
        course_members[course_name] = {} 
        for semester_id in course_list[course_name]:
            course_id = course_name + "-" + semester_id
            course_id_member_file = os.path.join(path, course_id+".csv")
            if os.path.isfile(course_id_member_file):
                members = list(pd.read_csv(course_id_member_file).Username.str.strip())
                course_members[course_name][semester_id] = members
            else:
                print("\x1b[6;30;43m" + "[WARNING] Course file not found: {}"
                      .format(course_id_member_file) + "; skipping....!" + "\x1b[0m")
    
    return course_members

def add_allowed_users(c, users):
    """
    Add users to JupyterHub allowed users
    args:
        c: JupyterHub config
        users: users to be added to JupyterHub
    """
    c.Authenticator.allowed_users |= users
    
def get_course_config_and_user(server_cfg):
    """
    Get course config and user list
    args:
        course_list_path: path to the course directory
    """
    
    course_cfg_and_user = {}
    if check_consecutive_keys(server_cfg, "nbgrader", "course_dir"):
        course_list_path = Path(server_cfg['nbgrader']['course_dir'])
    else:
        return course_cfg_and_user
    
    course_directories = [item for item in course_list_path.iterdir() 
                          if item.is_dir() and not item.name.startswith('.')]

    
    for course_path in course_directories:
        # loop through grader and student list
        role_directories = [item for item in course_path.iterdir() 
                            if item.is_dir() and not item.name.startswith('.')
                            and ("grader" in item.name.lower() or "student" in item.name.lower())]

        if not role_directories:
            continue
        
        course_cfg_and_user[course_path.name] = {}
        
        for role_path in role_directories:
            config_list_path = [item for item in role_path.iterdir() 
                                if item.is_file() and not item.name.startswith('.')
                                and ("yaml" in item.name.lower() or "yml" in item.name.lower())]
            user_list_path = [item for item in role_path.iterdir() 
                              if item.is_file() and not item.name.startswith('.')
                              and "csv" in item.name.lower()]

            if config_list_path:
                # get users for each course from each semester, the name of user list file
                # should represent the name of the course id for each semester
                course_cfg_and_user[course_path.name][role_path.name] = {}
                for cl in config_list_path:
                    course_cfg_and_user[course_path.name][role_path.name][cl.stem] = {}
                    # course config path
                    course_cfg_and_user[course_path.name][role_path.name][cl.stem]['course_config_path'] = cl

                    # load config once, to speed up the spawner if later the cfg is needed
                    course_config = load_yaml(cl)
                    if course_config is None:
                        course_config = {}
                    course_cfg_and_user[course_path.name][role_path.name][cl.stem]['course_config'] = course_config

                    user_path = [ccpath for ccpath in user_list_path if cl.stem in ccpath.stem]
                    user_list = []
                    if user_path:
                        user_list = list(pd.read_csv(user_path[0]).Username.str.strip())

                    course_cfg_and_user[course_path.name][role_path.name][cl.stem]['course_members'] = user_list
                    course_cfg_and_user[course_path.name][role_path.name][cl.stem]['course_members_path'] = user_path

    return course_cfg_and_user