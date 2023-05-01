# e2xhub: A JupyterHub extension for simplifying course management for teaching and exams

`e2xhub` provides a user-friendly JupyterHub configuration to allow graders to easily create courses and specify their requirements. We use YAML, a well-known declarative configuration language, to allow graders to set up courses, environments and resource allocation. We use [Zero to JupyterHub with Kubernetes (Z2JH)](https://z2jh.jupyter.org) to deploy JupyterHub on our Kubernetes cluster. `e2xhub` extends the capabilities of Z2JH, allowing us to deploy a more customizable JupyterHub. 

The main objectives include providing the ability to create or load courses for individual users, creating personalized profiles for each course e.g. personalized image and resource allocation (CPU, RAM, and GPU), and enabling multi-course and multi-grader support. All of these modifications can be easily made using YAML, without the need for a sysadmin to update the configuration.

`e2xhub` is well integrated with our nbgrader addon [`e2xgrader`](https://github.com/DigiKlausur/e2xgrader) that provides features for managing assignments, content creation and feedback generation. `e2xhub` is loaded on to JupyterHub configuration and updates the hub spawner.

### Usage

#### A simple example to use with Z2JH helm config:

```
config:
  extraConfig:
    import os
    import sys
    from e2xhub import E2xHub
    
    # configure e2x hub volumes
    e2xhub = E2xHub()
    e2xhub.ipython_config_path = '/etc/ipython/ipython_config.py'
    e2xhub.nbrader_config_path = '/etc/jupyter/nbgrader_config.py' 
    e2xhub.home_volume_name = 'disk2'
    e2xhub.home_volume_subpath = 'homes'
    e2xhub.home_volume_mountpath = '/home/jovyan'
    e2xhub.course_volume_name = 'disk2'
    e2xhub.course_volume_subpath = 'courses'
    e2xhub.course_volume_mountpath = '/home/jovyan/courses'
    e2xhub.exchange_volume_name = 'disk3'
    e2xhub.exchange_volume_subpath = 'nbgrader/exchanges'
    e2xhub.nbgrader_exchange_root = '/srv/nbgrader/exchange'
    e2xhub.share_volume_name = 'disk3'
    e2xhub.share_volume_subpath = 'shares/teaching'
    e2xhub.extra_volume_mountpath = '/srv/shares'

    # location of the config on the hub container, this can be from nfs mount
    config_root = '/srv/jupyterhub/config'
    config_file = os.path.join(config_root, 'config.yaml')
    server_name = "e2x_dev"

    if os.path.isfile(config_file):
        def get_profile_list(spawner):
            # Load server config every time profile is requested
            server_cfg = load_server_cfg(config_file, server_name)
            grader_user_dir = get_directory(server_cfg, "grader_user_dir")
            student_user_dir = get_directory(server_cfg, "student_user_dir")
            exam_user_dir = get_directory(server_cfg, "exam_user_dir")

            # Add default course list to kubespawner profile
            cmds, profile_list, username = e2xhub.init_profile_list(spawner,server_cfg)
            
            # Update profile list
            profile_list = e2xhub.configure_profile_list(spawner,
                                                         server_cfg,
                                                         grader_user_dir,
                                                         student_user_dir)

            return profile_list
        
        ### Get profile list ###
        c.KubeSpawner.profile_list = get_profile_list
        
        # Allow-root for singleuser
        c.KubeSpawner.cmd = ['start.sh','jupyterhub-singleuser','--allow-root']

        ### Pre spawn hook ###        
        async def pre_spawn_hook(spawner):
            await spawner.load_user_options()

            # Load server config every time profile is requested
            server_cfg = load_server_cfg(config_file, server_name)
            grader_user_dir = get_directory(server_cfg, "grader_user_dir")
            student_user_dir = get_directory(server_cfg, "student_user_dir")
            exam_user_dir = get_directory(server_cfg, "exam_user_dir")

            e2xhub.configure_pre_spawn_hook(spawner,
                                            server_cfg,
                                            grader_user_dir,
                                            student_user_dir)
            
        c.KubeSpawner.pre_spawn_hook = pre_spawn_hook

```
#### An example of config and allowed users in course list is located under [config](https://github.com/DigiKlausur/e2xhub/tree/main/config)
