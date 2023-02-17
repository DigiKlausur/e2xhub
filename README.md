# e2xhub: An Addon for Managing Courses for Teaching and Examination with JupyterHub on Kubernetes

`e2xhub` provides a user-friendly JupyterHub configuration to allow graders to easily create courses and specify their requirements. We use YAML, a well-known declarative configuration language, to allow graders to set up courses, environments and resource allocation. We use [Zero to JupyterHub with Kubernetes (Z2JH)](https://z2jh.jupyter.org) to deploy JupyterHub on our Kubernetes cluster. `e2xhub` extends the capabilities of Z2JH, allowing us to deploy a more customizable JupyterHub. 

The main objectives include providing the ability to create or load courses for individual users, creating personalized profiles for each course e.g. personalized image and resource allocation (CPU, RAM, and GPU), and enabling multi-course and multi-grader support. All of these modifications can be easily made using YAML, without the need for a sysadmin to update the configuration.

`e2xhub` is well integrated with our nbgrader addon [`e2xgrader`](https://github.com/DigiKlausur/e2xgrader) that provides features for managing assignments, content creation and feedback generation. `e2xhub` is loaded on to JupyterHub configuration and updates the hub spawner.

### Usage

A simple example to use with Z2JH helm config:

```
config:
  extraConfig:
    import os
    import sys
    from e2xhub.e2xhub import *

    # location of the config
    config_root = '/srv/jupyterhub/config'
    config_file = os.path.join(config_root, 'config-dev.yaml')
    server_name = "e2x_dev"

    if os.path.isfile(config_file):
        def get_profile_list(spawner):
            # Load server config every time profile is requested
            server_cfg = load_server_cfg(config_file, server_name)
            grader_user_dir = get_directory(server_cfg, "grader_user_dir")
            student_user_dir = get_directory(server_cfg, "student_user_dir")
            exam_user_dir = get_directory(server_cfg, "exam_user_dir")

            # Add default course list to kubespawner profile
            cmds, profile_list, username = init_profile_list(spawner,server_cfg)
            
            # Update profile list
            profile_list = configure_profile_list(spawner, server_cfg, grader_user_dir, student_user_dir)

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

            configure_pre_spawn_hook(spawner, server_cfg, grader_user_dir, student_user_dir)
            
        c.KubeSpawner.pre_spawn_hook = pre_spawn_hook

```
