import os
import yaml
import pandas as pd
import itertools

def load_yaml(config_file):
    """
    Load yaml file
    """
    configs = {}
    with open(config_file, 'r') as infile:
        configs = yaml.safe_load(infile)
    return configs

def check_consecutive_keys(config, *argv):
    """
    Check consecutive keys given config
    """
    for key in argv:
        if key in config:
            config = config[key]
        else:
            return False
    return True

def configure_volume_mount(volume_name,
                           volume_mountpath, 
                           volume_subpath,
                           read_only=False):
    """Configure volume mount in according to k8s specs
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
    Args:
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
                print ("\x1b[6;30;43m" + "[WARNING] Course file not found: {}"
                       .format(course_id_member_file) + "; skipping....!" + "\x1b[0m")
    
    return course_members

def add_allowed_users(c, users):
    """
    Add users to JupyterHub allowed users
    """
    c.Authenticator.allowed_users |= set(users)
    
def parse_exam_kernel_cfg(exam_kernel_cfg):
    """
    Parse exam kernel config
    """
    parsed_cfgs = []
    #spawner.log.debug("Configuring exam kernel")
    parsed_cfgs.append("echo from textwrap import dedent >> /etc/ipython/ipython_config.py")
    parsed_cfgs.append("echo c = get_config\(\) >> /etc/ipython/ipython_config.py")
    if 'allowed_imports' in exam_kernel_cfg:
        #spawner.log.debug("[exam_kernel] adding allowed imports")
        allowed_imports = exam_kernel_cfg['allowed_imports']
        joint_ai = "\["
        for allowed_import in allowed_imports:
            joint_ai = joint_ai + "\\'{}\\',".format(allowed_import)    
        joint_ai = "echo c.ExamKernel.allowed_imports = " + joint_ai + "\]" + " >> /etc/ipython/ipython_config.py"
        parsed_cfgs.append(joint_ai)              

    if 'init_code' in exam_kernel_cfg:
        #spawner.log.debug("[exam_kernel] adding init_code")
        init_code = exam_kernel_cfg['init_code']
        joint_ic = "\\'\\'\\'\\\\n"
        for ic in init_code:
            joint_ic = joint_ic + "{} \\\\n".format(ic)

        joint_ic = joint_ic + "\\'\\'\\'"
        joint_ic = "echo c.ExamKernel.init_code = " + joint_ic + " >> /etc/ipython/ipython_config.py"
        parsed_cfgs.append(joint_ic)              

    if 'allowed_magics' in exam_kernel_cfg:
        #spawner.log.debug("[exam_kernel] adding allowed_magics")
        allowed_magics = exam_kernel_cfg['allowed_magics']
        joint_am = "\["
        for allowed_magic in allowed_magics:
            joint_am = joint_am + "\\'{}\\',".format(allowed_magic)    
        joint_am = "echo c.ExamKernel.allowed_magics = " + joint_am + "\]" + " >> /etc/ipython/ipython_config.py"
        parsed_cfgs.append(joint_am)
        
    return parsed_cfgs

def parse_profile(spawner, course_cfg, course_id, 
                  cmds, role="student"):
    """
    Parse course profile to Kubespawner format
    args:
        spawner: spawner
        course_cfg: configuration of the given course id
        course_id: course_id where the config is applied to
        post_start_cmds: spawner post start commands
        pre_stop_cmds: spawner pre stop commands
        role: role of the user e.g. student, grader. This will reflect the course slug
    """
    # set image resources to default
    image = spawner.image 
    image_pull_policy = spawner.image_pull_policy
    cpu_limit = spawner.cpu_limit
    cpu_guarantee = spawner.cpu_guarantee
    mem_limit = "{:.1f}G".format(spawner.mem_limit/1000000000)
    mem_guarantee = "{:.1f}G".format(spawner.mem_guarantee/1000000000)
        
    if "image" in course_cfg:
        image = course_cfg["image"]
    if "pullPolicy" in course_cfg:
        image_pull_policy = course_cfg["pullPolicy"]
        
    profile_resources = {}
    if "resources" in course_cfg:
        profile_resources = course_cfg["resources"]
        if "cpu_guarantee" in profile_resources:
            cpu_guarantee = profile_resources["cpu_guarantee"]
        if "mem_guarantee" in profile_resources:
            mem_guarantee = profile_resources["mem_guarantee"]
        if "cpu_limit" in profile_resources:
            cpu_limit = profile_resources["cpu_limit"]
        if "mem_limit" in profile_resources:
            mem_limit = profile_resources["mem_limit"]
    
    # Default node affinity is user. Make sure you have 
    # at least one node labelled: hub.jupyter.org/node-purpose=user
    node_affinity = dict(
        matchExpressions=[
            dict(
                key="hub.jupyter.org/node-purpose",
                operator="In",
                values=["user"] if role=="student" else ["core"],
            )
        ],
    )

    node_info = "user"
    if "node_affinity" in profile_resources:
        node_affinity = profile_resources["node_affinity"]
        node_info = ""
        nodes = []
        for na in node_affinity["matchExpressions"]:
            nodes.extend(na["values"])
        node_info = "/".join(nodes)
        spawner.log.debug(f"Overriding node affinity, flavor {node_info}.")

    # Extra profile description
    extra_description = "<br>" 
    if 'extra_profile_description' in course_cfg:
        for description in course_cfg['extra_profile_description']:
            extra_description += description+"<br>" 
            
    # Description to show in each profile    
    course_description = f"resource: {cpu_limit}vCPUs {mem_limit} RAM, nodes: {node_info} <br> image: {image}, \
                          pullPolicy: {image_pull_policy} {extra_description}"
    spawner.log.debug(course_description)

    # course slug  must be unique for different role
    course_slug = course_id + f"--{role}" 
        
    parsed_profile = [
        {
            'display_name': f"{course_id} ({role})",
            'slug': '{}'.format(course_slug),
            'description': course_description,
            'kubespawner_override': {
                'cpu_limit': cpu_limit,
                'cpu_guarantee': cpu_guarantee,
                'mem_limit': '{}'.format(mem_limit),
                'mem_guarantee': '{}'.format(mem_guarantee),
                'image': image,
                'image_pull_policy': image_pull_policy,
                'lifecycle_hooks': {
                        "postStart": {
                            "exec": {
                                "command": ["/bin/sh", "-c", " && ".join(cmds)]
                            }
                        },
                        "preStop": {
                            "exec": {
                                "command": ["/bin/sh", "-c", "rm -rf /tmp/*"]
                            }
                        }
                },
                'node_affinity_required': [node_affinity]
            }
        } 
    ]
    
    return parsed_profile

def init_profile_list(spawner, server_cfg):
    """
    Initialize profile list and global hub configuration
    args:
        spawner: spawner object
        server_cfg: dictionary of server config
    """
    username = spawner.user.name

    # Default nbgrader commands
    cmds = []
    cmds.append(r"echo 'import os'  >> /etc/jupyter/nbgrader_config.py")
    cmds.append(r"echo 'c = get_config()'  >> /etc/jupyter/nbgrader_config.py")

    profile_list = []

    # Add commands to spawner (applied to all hub users)
    if check_consecutive_keys(server_cfg, "commands"):
        #spawner.log.debug("[Commands] Looking into extra command")
        extra_commands = server_cfg['commands']
        for extra_cmd in extra_commands:
            #spawner.log.debug("[Commands] Executing: %s", extra_cmd)
            cmds.append("{}".format(extra_cmd))              

    # Configure exam_kernel if config is given
    if check_consecutive_keys(server_cfg, "exam_kernel"):
        cmds.extend(parse_exam_kernel_cfg(server_cfg["exam_kernel"]))
            
    spawner.lifecycle_hooks = {
        "postStart": {
            "exec": {
                "command": ["/bin/sh", "-c", " && ".join(cmds)]
            }
        },
        "preStop": {
            "exec": {
                "command": ["/bin/sh", "-c", "rm -rf /tmp/*"]
            }
        }
    }

    # Default profile list
    profile_list.extend([
        {
        'display_name': 'Default',
        'slug': 'Default',
        'description': 'Default notebook server (home directory is not persistent)',
        'default': True,
        'kubespawner_override': {
            'cpu_limit': 2.0,
            'cpu_guarantee': 0.001,
            'mem_limit': '0.5G',
            'mem_guarantee': '0.25G',
            'image': 'ghcr.io/digiklausur/docker-stacks/notebook:latest',
            'image_pull_policy': 'IfNotPresent'
        }
        } 
    ])

    # Extra profile list
    if check_consecutive_keys(server_cfg, "extra_profile_list", "enabled"):
        if server_cfg["extra_profile_list"]["enabled"]:
            if check_consecutive_keys(server_cfg, "extra_profile_list", "profiles"):
                extra_profile_list = server_cfg['extra_profile_list']['profiles']
                for profile in extra_profile_list.keys():
                    parsed_profile = parse_profile(spawner, extra_profile_list, 
                                                   profile, cmds, 
                                                   role="student")
                    profile_list.extend(parsed_profile)


    return cmds, profile_list, username

def init_nbgrader_cfg(spawner,course_id, 
                      course_cfg, course_root,
                      nbgrader_cfg, course_list, 
                      cmds, sum_grader_cmds,
                      student=True):
    """
    Initialize nbgrader config
    """
    # Set course id and course root
    cmds.append("echo \'c.CourseDirectory.course_id = \"{}\"\'  >> /etc/jupyter/nbgrader_config.py".format(course_id))
    sum_grader_cmds += 1
    if not student:
        cmds.append("echo \'c.CourseDirectory.root = os.path.abspath(\"{}/{}\")\'  >> /etc/jupyter/nbgrader_config.py".format(course_root,course_id))
        sum_grader_cmds += 1      

    #Setup exchange, write all commands to enable the exchange
    if "exchange" in course_cfg:
        spawner.log.info("[exchange cmds] looking into course exchange cmds")
        exchange_commands = course_cfg['exchange']
        for exchange_cmd in exchange_commands:
            spawner.log.info("[exchange cmds] executing: %s", exchange_cmd)
            cmds.append("{}".format(exchange_cmd))      
            sum_grader_cmds += 1         
    else:
        #spawner.log.info("[exchange cmds] looking into default exchange cmds")
        if "default_exchange" in nbgrader_cfg:
            exchange_commands = nbgrader_cfg["default_exchange"]
            for exchange_cmd in exchange_commands:
                spawner.log.info("[exchange cmds] executing: %s", exchange_cmd)
                cmds.append("{}".format(exchange_cmd))      
                sum_grader_cmds += 1         

    # check whether inbound, outbound and feedback are personalized
    if "personalized_outbound" in course_cfg:
        personalized_outbound = course_cfg['personalized_outbound']
        spawner.log.info("[outbound] Using personalized outbound: %s", personalized_outbound)
        cmds.append(r"echo 'c.Exchange.personalized_outbound = {}' >> /etc/jupyter/nbgrader_config.py".format(personalized_outbound))
        sum_grader_cmds += 1
    else:
        spawner.log.info("[outbound] Using default outbound")

    if "personalized_inbound" in course_cfg:
        personalized_inbound = course_cfg['personalized_inbound']
        spawner.log.info("[inbound] Using personalized inbound directory: %s", personalized_inbound)
        cmds.append(r"echo 'c.Exchange.personalized_inbound = {}' >> /etc/jupyter/nbgrader_config.py".format(personalized_inbound))
        sum_grader_cmds += 1
    else:
        spawner.log.info("[inbound] Using default submit directory")

    if "personalized_feedback" in course_cfg:
        personalized_feedback = course_cfg['personalized_feedback']
        spawner.log.info("[feedback] Using personalized feedback directory: %s", personalized_feedback)
        cmds.append(r"echo 'c.Exchange.personalized_feedback = {}' >> /etc/jupyter/nbgrader_config.py".format(personalized_feedback))
        sum_grader_cmds += 1
    else:
        spawner.log.info("[inbound] Using default feedback directory")

    # add grader commands
    if not student:
        if nbgrader_cfg['grader_cmds']:
            spawner.log.info("[grader cmds] Looking into grader cmds")
            extra_commands = nbgrader_cfg['grader_cmds']
            len_extra_cmds = len(extra_commands)
            for extra_cmd in extra_commands:
                spawner.log.info("[grader cmds] executing: %s", extra_cmd)
                cmds.append("{}".format(extra_cmd))      
                sum_grader_cmds += 1   
            
    return cmds, sum_grader_cmds

def generate_course_profile(spawner, cmds, nbgrader_cfg,
                            course_list, allowed_users,
                            username, role="student"):
    
    # Configuration for grader's profile
    sum_grader_cmds = 0
    profile_list = []
    for course_name in allowed_users.keys():
        for semester_id in allowed_users[course_name]:
            if username in allowed_users[course_name][semester_id]:
                # set course id, that is the combination of course name and smt id
                course_id = course_name + "-" + semester_id
                # Set the course name and root
                #course_name = "-".join(course_id.split("-")[0:1]) #NLP-SS21 --> NLP 
                # ToDo: make this path as argument
                course_root = "/home/{}/courses/{}".format(username,
                                                           "-".join(course_id.split("-")[0:1]))

                # Initialize nbgrader config for the course
                course_cfg = course_list[course_name][semester_id]
                cmds, sum_grader_cmds = init_nbgrader_cfg(spawner,course_id, 
                                                          course_cfg, course_root, 
                                                          nbgrader_cfg, course_list, 
                                                          cmds, sum_grader_cmds,
                                                          student=False)

                # course specific commands e.g. enable exam mode for specific course
                if 'course_cmds' in course_cfg:
                    spawner.log.info("[course cmds] looking into course commands")
                    course_commands = course_list[course_id]['course_cmds']
                    for course_cmd in course_commands:
                        spawner.log.info("[course cmds] executing: %s", course_cmd)
                        cmds.append("{}".format(course_cmd))               
                        sum_grader_cmds += 1

                #Update post start commands
                post_start_cmds = ["/bin/sh", "-c", " && ".join(cmds)]

                parsed_profile = parse_profile(spawner, course_cfg, 
                                               course_id, cmds, 
                                               role=role)
                profile_list.extend(parsed_profile)

                # Clear grader commands for the current course
                del cmds[-sum_grader_cmds:]
                sum_grader_cmds = 0

    return profile_list

# set grader mounts
def configure_grader_volumes(spawner,
                             course_cfg,
                             selected_profile,
                             username, 
                             grader_user_dir,
                             server_mode, 
                             home_volume_name=None,
                             home_volume_mountpath=None,
                             home_volume_subpath=None,
                             course_volume_name=None,
                             course_volume_mountpath=None,
                             course_volume_subpath=None,
                             exchange_volume_name=None,
                             exchange_volume_mountpath=None,
                             exchange_volume_subpath="nbgrader/exchanges",
                             nbgrader_exchange_path="/srv/nbgrader/exchange",
                             uid=1000,
                             gid=1000):
    is_grader = False
    course_id = selected_profile.split("--")[0]
    
    # course name and semester id
    course_name, smt_id = course_id.split("-")
    
    # check if the use selected the grader course id, and he is a grader
    #if course_id in course_cfg:
    if check_consecutive_keys(course_cfg, course_name, smt_id):
        grader_course_cfg = course_cfg[course_name][smt_id] 
        # check if list of grader exists
        grader_course_id_member_file = os.path.join(grader_user_dir, course_id+".csv")
        
        if os.path.isfile(grader_course_id_member_file):
            spawner.log.debug("Found course file %s", grader_course_id_member_file)
            db_file_pd = pd.read_csv(grader_course_id_member_file)
            grader_list = list(db_file_pd.Username.apply(str))

            # mount home dir and the selected course dir if the user is grader
            if username in grader_list and course_id != "Default":
                # default home volume mountpath
                if not home_volume_mountpath:
                    home_volume_mountpath = '/home/{}'.format(username)
                
                # default home volume subpath
                if not home_volume_subpath:
                    home_volume_subpath = os.path.join("homes",
                                                       server_mode, 
                                                       "graders",
                                                       username)
                home_volume_mount = configure_volume_mount(home_volume_name,
                                                           home_volume_mountpath,
                                                           home_volume_subpath)
                spawner.log.debug("Grader home volume name is: %s", home_volume_name)
                if home_volume_name:
                    spawner.volume_mounts.append(home_volume_mount)
                    
                # mount previous course?
                mount_prev_courses = True
                if "mount_prev_courses" in grader_course_cfg:
                    mount_prev_courses = grader_course_cfg['mount_prev_courses']

                # check if student is the grader, and mount_prev_course is allowed
                # to avoid the student grader see other students submission from his/her batch
                if not mount_prev_courses and "2s" in username:
                    if not course_volume_mountpath:
                        course_volume_mountpath = '/home/{}/courses/{}/{}'.format(username,
                                                                                  course_name,
                                                                                  course_id)
                    if not course_volume_subpath:
                        course_volume_subpath = os.path.join("courses",
                                                              course_name,
                                                              course_id) 
                    
                else:
                    # todo: the problem with mounting all vols to graders, we cann't exclude student graders
                    # for the courses he/she was taking the course at the time. The reason is he/she is not
                    # allowed to see her/his peers submissions (according to Alex)
                    
                    if not course_volume_mountpath:
                        course_volume_mountpath = '/home/{}/courses/{}'.format(username,course_name)
                    
                    if not course_volume_subpath:
                        course_volume_subpath = os.path.join("courses", course_name) 
                
                course_volume_mount = configure_volume_mount(course_volume_name,
                                                           course_volume_mountpath,
                                                           course_volume_subpath)
                
                spawner.log.debug("Grader course volume name is: %s", course_volume_name)
                if course_volume_name:
                    spawner.volume_mounts.append(course_volume_mount)

                # set exchange volume
                if "exchange" in grader_course_cfg:
                    spawner.log.info("[grader][exchange] using given exchange service")
                else:
                    if not exchange_volume_mountpath:
                        exchange_volume_mountpath = os.path.join(nbgrader_exchange_path, course_id)
                    
                    exchange_volume_subpath = os.path.join(exchange_volume_subpath,
                                                           course_name, course_id) 
                    
                    exchange_volume_mount = configure_volume_mount(exchange_volume_name,
                                                           exchange_volume_mountpath,
                                                           exchange_volume_subpath,
                                                           read_only=False)
                    
                    spawner.log.debug("Grader exchange volume name is: %s", home_volume_name)
                    if exchange_volume_name:
                        spawner.volume_mounts.append(exchange_volume_mount)

                is_grader = True
                
                # set grader environment e.g. uid and gid
                spawner.log.debug("Changing uid and gid for grader: %s to %s %s", username, uid, gid)
                spawner.environment = {'NB_USER':username,'NB_UID':f'{uid}','NB_GID':f'{gid}'}
        else:
            spawner.log.warning("Grader course list not found: %s",grader_course_id_member_file)

    return is_grader

# set students volume mount
def configure_student_volumes(spawner, 
                              course_cfg, 
                              selected_profile, 
                              username, 
                              server_mode="teaching",
                              home_volume_name="disk2",
                              home_volume_subpath="homes",
                              home_volume_mountpath="/home/jovyan",
                              exchange_volume_name="disk3", 
                              exchange_volume_subpath="nbgrader/exchanges",
                              nbgrader_exchange_root="/srv/nbgrader/exchange",
                              uid=1000,
                              gid=1000):
    """
    Configure volume mounts for the student
    args:
      spawner: spawner object to which volume is configured
      course_cfg: list of available courses
      selected_profile: selected course by the user
      username: username of the user
      server_mode: whether teaching or exam mode, used to differentiate
      home directory location on the nfs server. It's useful when the exam and
      teaching servers are deployed on the same hub.
      home_volume_name: name of the home volume of the nfs client
      exchange_volume_name: name of the exchange volume of the nfs client
      exchange_volume_subpath: sub path of the exchange directory of all courses 
      on the nfs server
      nbgrader_exchange_root: nbgrader exchange root, default /srv/nbgrader/exchange
    """
    # currently the course slug for student is e.g. WuS-SS22--student (course_name-semester_id-role)
    # to differentiate between grader's and student's course slug
    student_course_id = selected_profile.split("--")[0]
    
    # course name and semester id
    course_name, smt_id = student_course_id.split("-")

    if check_consecutive_keys(course_cfg, course_name, smt_id):
        # course config for the given course_name and smt_id   
        student_course_cfg = course_cfg[course_name][smt_id]
        
        home_volume_subpath = os.path.join(home_volume_subpath,
                                           server_mode,
                                           "students", 
                                           student_course_id,
                                           username)
        
        home_volume_mount = configure_volume_mount(home_volume_name,
                                                   home_volume_mountpath,
                                                   home_volume_subpath)
        
        spawner.log.debug("Student home volume name is: %s", home_volume_name)
        if home_volume_name:
            spawner.volume_mounts.append(home_volume_mount)

        # setup exchange volumes if default nbgrader exchange is used
        if "exchange" in student_course_cfg:
            # ToDo
            spawner.log.info("[student][exchange] using given exchange service")
        else:
            #spawner.log.info("[student][exchange] using default exchange directory")
            # ToDo: make user_list_root as an argument
            user_list_root = os.path.join(config_root, "nbgrader", "teaching")
            course_id_member_file = os.path.join(user_list_root, student_course_id+".csv")
            if os.path.isfile(course_id_member_file):
                db_file_pd = pd.read_csv(course_id_member_file)
                user_list = list(db_file_pd.Username.apply(str))
                
                if username in user_list:
                    spawner.log.info("[pre spawn hook] found course %s for %s", student_course_id, username)
                    # check whether personalized inbound or outbound enabled
                    personalized_outbound = False
                    if "personalized_outbound" in student_course_cfg:
                        personalized_outbound = student_course_cfg['personalized_outbound']
                    if personalized_outbound:
                        if "assignment_id" in student_course_cfg:
                            assignment_id = student_course_cfg['assignment_id']
                        else:
                            spawner.log.info("[inbound] Using personalized outbound, but assignment_id is \
                                              not given. The assignment_id will be unknown")
                            assignment_id = "unknown-assignment"

                        outbound_mount_mountpath = os.path.join(nbgrader_exchange_root, 
                                                          student_course_id, 
                                                          "personalized-outbound", 
                                                          assignment_id, 
                                                          username)
                        outbound_volume_subpath = os.path.join(exchange_volume_subpath, 
                                                                        course_name, 
                                                                        student_course_id, 
                                                                        "personalized-outbound",
                                                                        assignment_id, username)
                    else: 
                        spawner.log.info("[outbound] Using default outbound")
                        outbound_mount_mountpath = os.path.join(nbgrader_exchange_root, 
                                                          student_course_id, 
                                                          "outbound")
                        outbound_volume_subpath = os.path.join(exchange_volume_subpath, 
                                                                        course_name, 
                                                                        student_course_id, 
                                                                        "outbound")
                    
                    outbound_volume_mount = configure_volume_mount(exchange_volume_name,
                                                               outbound_mount_mountpath,
                                                               outbound_volume_subpath,
                                                               read_only=True)

                    # configure inbound
                    personalized_inbound = False
                    if "personalized_inbound" in student_course_cfg:
                        personalized_inbound = student_course_cfg['personalized_inbound']
                    if personalized_inbound:
                        spawner.log.info("[inbound] Using personalized inbound directory")
                        inbound_volume_mountpath = os.path.join(nbgrader_exchange_root, 
                                                         student_course_id, 
                                                         "personalized-inbound", 
                                                         username)
                        inbound_volume_subpath = os.path.join(exchange_volume_subpath,
                                                                       course_name, 
                                                                       student_course_id, 
                                                                       "personalized-inbound", 
                                                                       username)
                    else:
                        spawner.log.info("[inbound] Using default submit directory")
                        inbound_volume_mountpath = os.path.join(nbgrader_exchange_root, 
                                                         student_course_id, 
                                                         "inbound")
                        inbound_volume_subpath = os.path.join(exchange_volume_subpath, 
                                                                       course_name, 
                                                                       student_course_id, 
                                                                       "inbound")
                    
                    inbound_volume_mount = configure_volume_mount(exchange_volume_name,
                                                               inbound_volume_mountpath,
                                                               inbound_volume_subpath)
                    # configure feedback
                    personalized_feedback = False
                    if "personalized_feedback" in student_course_cfg:
                        personalized_feedback = student_course_cfg['personalized_feedback']
                    if personalized_feedback:
                        spawner.log.info("[feedback] using personalized feedback directory")
                        feedback_volume_mountpath = os.path.join(nbgrader_exchange_root, 
                                                          student_course_id, 
                                                          "personalized-feedback", 
                                                          username)
                        feedback_volume_subpath = os.path.join(exchange_volume_subpath,
                                                                        course_name, 
                                                                        student_course_id, 
                                                                        "personalized-feedback", 
                                                                        username)
                    else:
                        spawner.log.info("[feedback] using default feedback directory")
                        feedback_volume_mountpath = os.path.join(nbgrader_exchange_root, 
                                                          student_course_id, 
                                                          "feedback")
                        feedback_volume_subpath = os.path.join(exchange_volume_subpath, 
                                                               course_name, 
                                                               student_course_id, 
                                                               "feedback")
                    
                    feedback_volume_mount = configure_volume_mount(exchange_volume_name,
                                                               feedback_volume_mountpath,
                                                               feedback_volume_subpath,
                                                               read_only=True)
                    
                    spawner.log.debug("Student exchange/inbound volume name is: %s", exchange_volume_name)
                    if exchange_volume_name:
                        spawner.volume_mounts.append(outbound_volume_mount)
                        spawner.volume_mounts.append(inbound_volume_mount)
                        spawner.volume_mounts.append(feedback_volume_mount)
                    else:
                        spawner.log.warning("Student exchange volume name is: %s",exchange_volume_name,
                                            "consult k8s admin to provide the volume for exchange")
            else:
                spawner.log.warning("Course file not found: %s",course_id_member_file)


        # set student uid=1000, gid=1000. This translates student user to jovyan user
        spawner.environment = {'NB_USER':username,'NB_UID':f'{uid}','NB_GID':f'{gid}'}
        spawner.log.info("UID and GID for %s is changed to %s", username, spawner.environment)
        
def configure_extra_course_volumes(spawner,
                                selected_profile, 
                                share_volume_name,
                                share_volume_subpath,
                                extra_volume_mountpath = "/srv/shares",
                                read_only=True):
    """
    Add extra volume mounts for a particular course (selected profile).
    Public directory /srv/shares/public is always mounted to all courses,
    and is accessible to all users in the hub.
    Whereas private volume mount is only accessible to the registered users.
    args:
      spawner: spawner object
      selected_profile: selected course profile
      share_volume_name: name of the shared volume
      share_volume_subpath: subpath of the volume in the nfs server shared dir
      extra_volume_mountpath: path where the extra mounts to be mounted
      read_only: whether the vol mounts are read_only to users
    """
    # mount public/common dirs: e.g. instructions and cheatsheets
    public_volume_mountpath = f"{extra_volume_mountpath}/public" 
    public_volume_subpath = os.path.join(share_volume_subpath, "public")
    
    public_volume_mount = configure_volume_mount(share_volume_name,
                                                 public_volume_mountpath,
                                                 public_volume_subpath,
                                                 read_only=read_only)
    
    # course specific shared files / dirs within the selected course
    share_course_id = selected_profile.split("--")[0]
    share_course_name = share_course_id.split("-")[0]
    private_volume_mountpath = f"{extra_volume_mountpath}/{share_course_name}"
    private_volume_subpath = os.path.join(share_volume_subpath, 
                                                   "courses", 
                                                   "{}".format(share_course_name))
    
    private_volume_mount = configure_volume_mount(share_volume_name,
                                                 private_volume_mountpath,
                                                 private_volume_subpath,
                                                 read_only=read_only)
    
    spawner.log.debug("Extra volume name is: %s", share_volume_name)
    if share_volume_name:
        spawner.volume_mounts.append(public_volume_mount)
        spawner.volume_mounts.append(private_volume_mount)
    else:
        spawner.log.warning("Extra volume name is: %s",share_volume_name,
                            "consult k8s admin to provide the volume for exchange")
    
def set_extra_volume_mounts(spawner, vol_mounts, read_only=True):
    """
    Add extra volume mounts
    args:
      spawner: spawner object
      vol_mounts: dictionary of vol mounts to be added to the spawner
      read_only: whether the vol mounts are read_only to users
    """
    # add mount if it does not exists, is it the best way to do?              
    # automatically add rw share dir for grader, and ro share for students
    for vmount in vol_mounts['volume_mounts'].values():
        spawner.log.info("Add extra volume mount from config:%s",vmount['mountPath'])
        extra_vmount = configure_volume_mount(vmount['name'],
                                              vmount['mountPath'],
                                              vmount['subPath'],
                                              read_only=read_only)
        spawner.volume_mounts.append(extra_vmount)