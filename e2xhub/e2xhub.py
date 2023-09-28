import os
from pathlib import Path

from .utils import *
import pandas as pd
from traitlets import Unicode, List
from traitlets.config import LoggingConfigurable


class E2xHub(LoggingConfigurable):
    """
    E2xHub provides functionalities to enable multi-course and multi-grader support
    in JupyterHub on Kubernetes such as personalized profiles, resource allocation,
    and course management.
    """

    ipython_config_path = Unicode(
        "/etc/ipython/ipython_config.py",
        help="""
        Path to the ipython_config.py
        """,
    ).tag(config=True)

    nbgrader_config_path = Unicode(
        "/etc/jupyter/nbgrader_config.py",
        help="""
        Path to the nbgrader_config.py
        """,
    ).tag(config=True)

    home_volume_name = Unicode(
        "disk2",
        help="""
        Home volume name on the nfs client
        """,
    ).tag(config=True)

    home_volume_subpath = Unicode(
        "homes",
        help="""
        Home volume subpath on the nfs server 
        they share the same path
        """,
    ).tag(config=True)

    course_volume_name = Unicode(
        "disk2",
        help="""
        Home volume name on the nfs client
        """,
    ).tag(config=True)

    course_volume_subpath = Unicode(
        "courses",
        help="""
        Course volume subpath for graders on the nfs server 
        they share the same path
        """,
    ).tag(config=True)

    course_volume_dir = Unicode(
        "/home/jovyan/courses",
        help="""
        Course volume mount dir for graders on the nfs client.
        This directory will be mounted to user's home.
        """,
    ).tag(config=True)

    exchange_volume_name = Unicode(
        "disk3",
        help="""
        Exchange volume name on the nfs client
        """,
    ).tag(config=True)

    exchange_volume_subpath = Unicode(
        "nbgrader/exchanges",
        help="""
        Exchange volume subpath for graders on the nfs server 
        they share the same path
        """,
    ).tag(config=True)

    nbgrader_exchange_root = Unicode(
        "/srv/nbgrader/exchange",
        help="""
        Exchange volume mount path on the nfs client. This will be followed 
        by course_id e.g. /srv/nbgrader/exchange/CourseID-WS20
        """,
    ).tag(config=True)

    share_volume_name = Unicode(
        "disk3",
        help="""
        Share volume name on the nfs client
        """,
    ).tag(config=True)

    share_volume_subpath = Unicode(
        "shares/teaching",
        help="""
        Share volume subpath for graders on the nfs server 
        they share the same path
        """,
    ).tag(config=True)

    extra_volume_mountpath = Unicode(
        "/srv/shares",
        help="""
        Extra volume mount path
        """,
    ).tag(config=True)

    course_cfg_volume_mountpath = Unicode(
        "/srv/disk-01/jupyterhub/nbgrader/courses",
        help="""
        Config volume mount path for the course grader
        """,
    ).tag(config=True)
    course_cfg_volume_name = Unicode(
        "disk1",
        help="""
        Course config volume name on the nfs client
        """,
    ).tag(config=True)

    course_cfg_volume_subpath = Unicode(
        "jupyterhub/nbgrader/courses",
        help="""
        Course config volume subpath for graders on the nfs server 
        they share the same path
        """,
    ).tag(config=True)

    config_volume_mountpath = Unicode(
        "/srv/disk-01/jupyterhub",
        help="""
        Config volume mount path for admins
        """,
    ).tag(config=True)

    config_volume_name = Unicode(
        "disk1",
        help="""
        Course config volume name on the nfs client
        """,
    ).tag(config=True)

    config_volume_subpath = Unicode(
        "jupyterhub",
        help="""
        Config volume subpath for admins on the nfs server 
        they share the same path
        """,
    ).tag(config=True)

    student_uid = Unicode(
        "1000",
        help="""
        Linux UID for student
        """,
    ).tag(config=True)

    student_gid = Unicode(
        "1000",
        help="""
        Linux GID for student
        """,
    ).tag(config=True)

    grader_uid = Unicode(
        "2000",
        help="""
        Linux UID for grader
        """,
    ).tag(config=True)

    grader_gid = Unicode(
        "2000",
        help="""
        Linux GID for grader
        """,
    ).tag(config=True)

    student_node = List(
        [dict(key="hub.jupyter.org/node-purpose", operator="In", values=["user"])],
        help="""
        Default node label allocated for students
        """,
    ).tag(config=True)

    grader_node = List(
        [dict(key="hub.jupyter.org/node-purpose", operator="In", values=["core"])],
        help="""
        Default node label allocated for students
        """,
    ).tag(config=True)

    def __init__(self, **kwargs):
        super(E2xHub, self).__init__(**kwargs)

    def parse_exam_kernel_cfg(self, spawner, exam_kernel_cfg):
        """
        Parse exam kernel config
        args:
            spawner: kubespawner object
            exam_kernel_cfg: exam kernel configuration to parse
        """
        parsed_cfgs = []
        spawner.log.debug("Configuring exam kernel")
        parsed_cfgs.append(
            f"echo from textwrap import dedent >> {self.ipython_config_path}"
        )
        parsed_cfgs.append(f"echo c = get_config\(\) >> {self.ipython_config_path}")
        if "allowed_imports" in exam_kernel_cfg:
            spawner.log.debug("[exam_kernel] adding allowed imports")
            allowed_imports = exam_kernel_cfg["allowed_imports"]
            joint_ai = "\["
            for allowed_import in allowed_imports:
                joint_ai = joint_ai + "\\'{}\\',".format(allowed_import)
            joint_ai = (
                "echo c.ExamKernel.allowed_imports = "
                + joint_ai
                + "\]"
                + f" >> {self.ipython_config_path}"
            )
            parsed_cfgs.append(joint_ai)

        if "init_code" in exam_kernel_cfg:
            spawner.log.debug("[exam_kernel] adding init_code")
            init_code = exam_kernel_cfg["init_code"]
            joint_ic = "\\'\\'\\'\\\\n"
            for ic in init_code:
                joint_ic = joint_ic + "{} \\\\n".format(ic)

            joint_ic = joint_ic + "\\'\\'\\'"
            joint_ic = (
                "echo c.ExamKernel.init_code = "
                + joint_ic
                + f" >> {self.ipython_config_path}"
            )
            parsed_cfgs.append(joint_ic)

        if "allowed_magics" in exam_kernel_cfg:
            spawner.log.debug("[exam_kernel] adding allowed_magics")
            allowed_magics = exam_kernel_cfg["allowed_magics"]
            joint_am = "\["
            for allowed_magic in allowed_magics:
                joint_am = joint_am + "\\'{}\\',".format(allowed_magic)
            joint_am = (
                "echo c.ExamKernel.allowed_magics = "
                + joint_am
                + "\]"
                + f" >> {self.ipython_config_path}"
            )
            parsed_cfgs.append(joint_am)

        return parsed_cfgs

    def create_course_profile(self, spawner, server_cfg, course_name, role="student"):
        """
        Parse course profile to KubesPawner format and configure default resources
        for all courses. This will be overrided by the course config if given
        args:
            spawner: spawner
            course_name: name of the course
            role: role of the user e.g. student, grader. This will reflect the course slug
        """
        image = server_cfg.get("image", spawner.image)
        image_pull_policy = server_cfg.get("pullPolicy", spawner.image_pull_policy)

        if role == "grader":
            user_resources = server_cfg.get("grader_resources", {})
        else:
            user_resources = server_cfg.get("resources", {})

        cpu_guarantee = user_resources.get("cpu_guarantee", spawner.cpu_guarantee)
        cpu_limit = user_resources.get("cpu_limit", spawner.cpu_limit)
        # convert memory to GB
        mem_guarantee = user_resources.get(
            "mem_guarantee", "{:.1f}G".format(spawner.mem_guarantee / 1000000000)
        )
        mem_limit = user_resources.get(
            "mem_limit", "{:.1f}G".format(spawner.mem_limit / 1000000000)
        )

        # Default user node affinity
        user_node_affinity = spawner.node_affinity_required
        if "node_affinity" in user_resources:
            user_node_affinity = user_resources["node_affinity"]

        # course slug  must be unique for different role
        # here we use {course_name}+{role} as slug
        # which also correspods to the key in the course config
        # e.g. MRC-Teaching+grader
        course_slug = f"{course_name}+{role}"

        # default course display name
        course_display_name = f"{course_name} ({role})"

        # if grader, set color to blue to make it distinct with stud color
        if role == "grader":
            course_display_name = (
                f'<span style="color:blue;">{course_display_name} - grader </span>'
            )
        else:
            course_display_name = f"{course_display_name} - student"
        spawner.log.debug(course_display_name)

        # parse profile
        parsed_course_profile = {
            "display_name": f"{course_display_name}",
            "slug": f"{course_slug}",
            "profile_options": {
                "course_id_slug": {
                    "display_name": "Semester",
                    "choices": {},
                },
            },
            "kubespawner_override": {"node_affinity_required": [user_node_affinity]},
        }

        return parsed_course_profile

    def create_semester_profile(
        self,
        spawner,
        course_profile,
        course_cfg,
        course_name,
        course_id,
        cmds,
        role="student",
    ):
        """
        Create a choice for each course id (each semester) and configure the env
        and resources
        args:
            spawner: spawner
            course_cfg: configuration of the given course id
            course_profile: course profile
            course_id: course_id where the config is applied to
            post_start_cmds: spawner post start commands
            cmds: spawner pre stop commands
            role: role of the user e.g. student, grader. This will reflect the course slug
        """
        verbose_profile_list = course_cfg.get("verbose_profile_list", False)
        # set image resources to default
        image = course_cfg.get("image", spawner.image)
        image_pull_policy = course_cfg.get("pullPolicy", spawner.image_pull_policy)

        profile_resources = course_cfg.get("resources", {})
        cpu_guarantee = profile_resources.get("cpu_guarantee", spawner.cpu_guarantee)
        cpu_limit = profile_resources.get("cpu_limit", spawner.cpu_limit)
        # convert memory to GB
        mem_guarantee = profile_resources.get(
            "mem_guarantee", "{:.1f}G".format(spawner.mem_guarantee / 1000000000)
        )
        mem_limit = profile_resources.get(
            "mem_limit", "{:.1f}G".format(spawner.mem_limit / 1000000000)
        )

        # schedule user by default to nodes that have label "user"
        node_info = "user"
        course_node_affinity = []
        if "node_affinity" in profile_resources:
            course_node_affinity = profile_resources["node_affinity"]
            node_info = ""
            nodes = []
            for na in course_node_affinity["matchExpressions"]:
                nodes.extend(na["values"])
            node_info = "/".join(nodes)
            spawner.log.debug(f"Overriding node affinity, flavor {node_info}.")

        # Extra profile description
        extra_description = "<br>"
        if "extra_profile_description" in course_cfg:
            for description in course_cfg["extra_profile_description"]:
                extra_description += description + "<br>"

        # Description to show in each profile
        course_description = (
            f"resource: {cpu_limit}vCPUs {mem_limit} RAM,"
            + f"nodes: {node_info} <br> image: {image},"
            + f"pullPolicy: {image_pull_policy} {extra_description}"
        )
        spawner.log.debug(course_description)

        if verbose_profile_list:
            course_profile["description"] = course_description

        # course slug  must be unique for different role
        # here we use {course_name}+{role}+{course_id} as slug
        # which also correspods to the key in the course config
        # e.g. MRC-Teaching+grader+MRC-Teaching-SS23
        # override course_name and course_id if given in its course config
        course_name = course_cfg.get("course_name", course_name)
        course_id = course_cfg.get("course_id", course_id)
        course_id_slug = f"{course_name}+{role}+{course_id}"

        # override course display name if given in course config
        choice_display_name = course_cfg.get("choice_display_name", course_id)
        spawner.log.debug(choice_display_name)

        # convert profile to KubeSpawner format
        parsed_semester_profile = {
            f"{course_id_slug}": {
                "display_name": choice_display_name,
                "default": course_cfg.get("default", False),
                "kubespawner_override": {
                    "cpu_limit": cpu_limit,
                    "cpu_guarantee": cpu_guarantee,
                    "mem_limit": "{}".format(mem_limit),
                    "mem_guarantee": "{}".format(mem_guarantee),
                    "image": image,
                    "image_pull_policy": image_pull_policy,
                    "lifecycle_hooks": {
                        "postStart": {
                            "exec": {"command": ["/bin/sh", "-c", " && ".join(cmds)]}
                        },
                        # todo: is this needed?
                        "preStop": {
                            "exec": {"command": ["/bin/sh", "-c", "rm -rf /tmp/*"]}
                        },
                    },
                    **(
                        {"node_affinity_required": [course_node_affinity]}
                        if course_node_affinity
                        else {}
                    ),
                },
            }
        }

        # add choices
        course_profile["profile_options"]["course_id_slug"]["choices"].update(
            parsed_semester_profile
        )
        # override course display name if given in each course id
        course_display_name = course_cfg.get(
            "course_display_name", course_profile["display_name"]
        )
        if role == "grader":
            if "grader" not in course_display_name:
                course_display_name = (
                    f'<span style="color:blue;">{course_display_name} - grader</span>'
                )
        else:
            if "student" not in course_display_name:
                course_display_name = f"{course_display_name} - student"

        course_profile["display_name"] = course_display_name

    def init_profile_list(self, spawner, server_cfg):
        """
        Initialize profile list and global hub configuration
        args:
            spawner: spawner object
            server_cfg: dictionary of server config
        """
        username = spawner.user.name

        # Default nbgrader commands
        cmds = []
        profile_list = []

        # Add commands to spawner (applied to all hub users)
        if check_consecutive_keys(server_cfg, "commands"):
            spawner.log.debug("[Commands] Looking into extra command")
            extra_commands = server_cfg["commands"]
            for extra_cmd in extra_commands:
                spawner.log.debug("[Commands] Executing: %s", extra_cmd)
                cmds.append("{}".format(extra_cmd))

        # Configure exam_kernel if config is given
        if check_consecutive_keys(server_cfg, "exam_kernel"):
            cmds.extend(self.parse_exam_kernel_cfg(spawner, server_cfg["exam_kernel"]))

        spawner.lifecycle_hooks = {
            "postStart": {"exec": {"command": ["/bin/sh", "-c", " && ".join(cmds)]}},
            "preStop": {"exec": {"command": ["/bin/sh", "-c", "rm -rf /tmp/*"]}},
        }

        # Default profile list
        profile_list.extend(
            [
                {
                    "display_name": "Default",
                    "slug": "Default",
                    "description": "Default notebook server (home directory is not persistent)",
                    "default": True,
                    "kubespawner_override": {
                        "cpu_limit": 2.0,
                        "cpu_guarantee": 0.001,
                        "mem_limit": "0.5G",
                        "mem_guarantee": "0.25G",
                        "image": "ghcr.io/digiklausur/docker-stacks/notebook:latest",
                        "image_pull_policy": "IfNotPresent",
                    },
                }
            ]
        )

        return cmds, profile_list, username

    def configure_nbgrader(
        self,
        spawner,
        nbgrader_cfg,
        course_cfg,
        course_id,
        course_id_path,
        cmds,
        sum_cmds,
        student=True,
    ):
        """
        Initialize nbgrader config
        args:
            spawner: kubespawner object
            nbgrader_cfg: global and default nbgrader config, this is overrided by the course-specific
            nbgrader config
            course_cfg: course configuration containing course list with its configs
            course_id: course id e.g. MRC-Teaching-SS23
            course_id_path: path to the course id root e.g. $HOME/courses/MRC-Teaching/MRC-Teaching-SS23
            cmds: commands executed when the server starts spawning
            sum_cmds: number of commands before nbgrader related commands added
            student: whether the server is configured for students
        """
        # Set course id and course root
        cmds.append(
            f"echo 'c.CourseDirectory.course_id = \"{course_id}\"'  >> {self.nbgrader_config_path}"
        )
        sum_cmds += 1
        if not student:
            cmds.append(
                f"echo 'c.CourseDirectory.root = \"{course_id_path}\"'  >> {self.nbgrader_config_path}"
            )
            sum_cmds += 1

        # Additional nbgrader commands
        spawner.log.debug("[nbgrader_cmds] looking into default exchange cmds")
        if "nbgrader_cmds" in nbgrader_cfg:
            nbgrader_commands = nbgrader_cfg["nbgrader_cmds"]
            for nbg_cmd in nbgrader_commands:
                spawner.log.debug("[nbgrader_cmds] executing: %s", nbg_cmd)
                cmds.append("{}".format(nbg_cmd))
                sum_cmds += 1

        # Configure exchange if given in nbgrader_cfg
        exchange_configured = False
        if "default_exchange" in nbgrader_cfg:
            personalized_outbound = nbgrader_cfg["default_exchange"].get(
                "personalized_outbound", False
            )
            personalized_inbound = nbgrader_cfg["default_exchange"].get(
                "personalized_inbound", False
            )
            personalized_feedback = nbgrader_cfg["default_exchange"].get(
                "personalized_feedback", False
            )
            exchange_configured = True

        # Configure exchange if given in course_exchange
        if "course_exchange" in course_cfg:
            personalized_outbound = course_cfg["course_exchange"].get(
                "personalized_outbound", False
            )
            personalized_inbound = course_cfg["course_exchange"].get(
                "personalized_inbound", False
            )
            personalized_feedback = course_cfg["course_exchange"].get(
                "personalized_feedback", False
            )
            exchange_configured = True

        # Add nbgrader exchange config
        if exchange_configured:
            cmds.append(
                f"echo 'c.Exchange.personalized_outbound = {personalized_outbound}' >> {self.nbgrader_config_path}"
            )
            sum_cmds += 1
            cmds.append(
                f"echo 'c.Exchange.personalized_inbound = {personalized_inbound}' >> {self.nbgrader_config_path}"
            )
            sum_cmds += 1
            cmds.append(
                f"echo 'c.Exchange.personalized_feedback = {personalized_feedback}' >> {self.nbgrader_config_path}"
            )
            sum_cmds += 1

            spawner.log.info(
                "[outbound] Using personalized outbound: %s", personalized_outbound
            )
            spawner.log.info(
                "[inbound] Using personalized inbound directory: %s",
                personalized_inbound,
            )
            spawner.log.info(
                "[feedback] Using personalized feedback directory: %s",
                personalized_feedback,
            )

        # add grader commands
        if not student:
            if nbgrader_cfg["grader_cmds"]:
                spawner.log.info("[grader cmds] Looking into grader cmds")
                extra_commands = nbgrader_cfg["grader_cmds"]
                len_extra_cmds = len(extra_commands)
                for extra_cmd in extra_commands:
                    spawner.log.info("[grader cmds] executing: %s", extra_cmd)
                    cmds.append("{}".format(extra_cmd))
                    sum_cmds += 1

        return cmds, sum_cmds

    def generate_course_profile(
        self, spawner, server_cfg, nbgrader_cfg, cmds, course_cfg_list, role="student"
    ):
        """
        Generate course profile from the given course list and config
        args:
            spawner: kubespawner object
            nbgrader_cfg: global and default nbgrader config, this is overrided by the course-specific
            nbgrader config
            course_cfg_list: course configuration containing course list with its configs
            cmds: commands executed when the server starts spawning
            role: role of the current user e.g. student or grader
        """
        # keep track of commands for each course
        sum_cmds = 0
        profile_list = []
        # if no course config, return empty profile
        if not course_cfg_list:
            spawner.log.warning(f"Course config is empty, returning empty profile")
            return profile_list

        for course_name in course_cfg_list.keys():
            if role not in course_cfg_list[course_name]:
                spawner.log.warning(
                    f"Course {course_name} does not have config for role {role}"
                )
                continue

            course_profile = self.create_course_profile(
                spawner, server_cfg, course_name, role
            )

            is_user_course_member = False
            for course_id in course_cfg_list[course_name][role].keys():
                course_members = course_cfg_list[course_name][role][course_id][
                    "course_members"
                ]
                if spawner.user.name in course_members:
                    course_id_path = (
                        f"/home/{spawner.user.name}/courses/{course_name}/{course_id}"
                    )

                    # Add configuration for each course
                    curr_course_cfg = course_cfg_list[course_name][role][course_id][
                        "course_config"
                    ]
                    cmds, sum_cmds = self.configure_nbgrader(
                        spawner,
                        nbgrader_cfg,
                        curr_course_cfg,
                        course_id,
                        course_id_path,
                        cmds,
                        sum_cmds,
                        student=False if role == "grader" else True,
                    )

                    # course specific commands e.g. enable exam mode for specific course
                    if "course_cmds" in curr_course_cfg:
                        spawner.log.info("[course cmds] looking into course commands")
                        course_commands = curr_course_cfg["course_cmds"]
                        for course_cmd in course_commands:
                            spawner.log.info("[course cmds] executing: %s", course_cmd)
                            cmds.append("{}".format(course_cmd))
                            sum_cmds += 1

                    # update post start commands
                    post_start_cmds = ["/bin/sh", "-c", " && ".join(cmds)]

                    self.create_semester_profile(
                        spawner,
                        course_profile,
                        curr_course_cfg,
                        course_name,
                        course_id,
                        cmds,
                        role=role,
                    )

                    # Clear commands for the current course
                    del cmds[-sum_cmds:]
                    sum_cmds = 0
                    is_user_course_member = True

            # only show profile to members registered in the courses
            # at least the user exist in one of the choices
            if is_user_course_member:
                # sort semester choices based on semester
                semester_choices = course_profile["profile_options"]["course_id_slug"][
                    "choices"
                ]
                sorted_semester_choices = sorted(
                    semester_choices.items(), key=lambda x: x[1]["display_name"]
                )
                course_profile["profile_options"]["course_id_slug"]["choices"] = dict(
                    sorted_semester_choices
                )
                profile_list.append(course_profile)

        # sort profile alphabetically
        profile_list = sorted(profile_list, key=lambda x: x["display_name"])

        return profile_list

    def configure_grader_volumes(
        self, spawner, server_cfg, course_cfg_list, admin_user=False
    ):
        """
        Configure grader volumes
        args:
          spawner: spawner object
          server_cfg: server configuration
          course_cfg_list: course config
          admin_user: whether current user is admin or not
        """
        # check server mode (exam|teaching) otherwise set to teaching
        server_mode = server_cfg.get("mode", "teaching")

        selected_profile = spawner.user_options["course_id_slug"]
        course_name, role, course_id = selected_profile.split("+")
        username = spawner.user.name

        course_cfg = course_cfg_list[course_name]["grader"][course_id]
        course_members = course_cfg["course_members"]

        # mount home dir and the selected course dir if the user is grader
        if username in course_members:
            # Load grader course config if given
            grader_course_cfg = course_cfg["course_config"]

            # home volume subpath for grader
            home_volume_mountpath = f"/home/{username}"
            home_volume_subpath = os.path.join(
                self.home_volume_subpath, server_mode, "graders", username
            )
            home_volume_mount = configure_volume_mount(
                self.home_volume_name, home_volume_mountpath, home_volume_subpath
            )

            spawner.log.debug("Grader home volume name: %s", self.home_volume_name)
            spawner.log.debug("Grader home volume mountpath: %s", home_volume_mountpath)
            spawner.log.debug("Grader home volume subpath: %s", home_volume_subpath)
            if self.home_volume_name:
                spawner.volume_mounts.append(home_volume_mount)

            course_volume_mountpath = f"/home/{username}/courses/{course_name}"
            course_volume_subpath = os.path.join(
                self.course_volume_subpath, course_name
            )
            course_volume_mount = configure_volume_mount(
                self.course_volume_name, course_volume_mountpath, course_volume_subpath
            )

            spawner.log.debug("Grader course volume name: %s", self.course_volume_name)
            spawner.log.debug(
                "Grader course volume mountpath: %s", course_volume_mountpath
            )
            spawner.log.debug("Grader course volume subpath: %s", course_volume_subpath)

            if self.course_volume_name:
                spawner.volume_mounts.append(course_volume_mount)

            nbgrader_cfg = get_nbgrader_cfg(server_cfg)
            exchange_configured = (
                True
                if (
                    "default_exchange" in nbgrader_cfg
                    or "course_exchange" in grader_course_cfg
                )
                else False
            )
            print("#############################")
            print("course cfg", course_cfg)
            print(
                "default_exchange: ",
                True if "default_exchange" in nbgrader_cfg else False,
            )
            print(
                "course exchange: ", True if "course_exchange" in course_cfg else False
            )
            print("configrued: ", exchange_configured)
            # configure exchange volume mount
            if exchange_configured:
                exchange_volume_mountpath = os.path.join(
                    self.nbgrader_exchange_root, course_id
                )
                exchange_volume_subpath = os.path.join(
                    self.exchange_volume_subpath, course_name, course_id
                )
                exchange_volume_mount = configure_volume_mount(
                    self.exchange_volume_name,
                    exchange_volume_mountpath,
                    exchange_volume_subpath,
                    read_only=False,
                )
                spawner.log.debug(
                    "[grader_exchange] Grader exchange volume name is: %s",
                    self.exchange_volume_name,
                )
                if self.exchange_volume_name:
                    spawner.volume_mounts.append(exchange_volume_mount)
            else:
                spawner.log.warning(
                    "[grader_exchange] Default exchange is not configured"
                )

            # mount server config to admin users and if it's enabled in the server config
            # this will allow admins to modify config in their notebooks server
            mount_server_config = server_cfg.get("mount_server_config", False)
            if admin_user and mount_server_config:
                config_volume_mount = configure_volume_mount(
                    self.config_volume_name,
                    self.config_volume_mountpath,
                    self.config_volume_subpath,
                    read_only=False,
                )
                if self.config_volume_name:
                    spawner.log.debug(
                        "Mounting config volume to admin user: %s", username
                    )
                    spawner.volume_mounts.append(config_volume_mount)

            # mount course config to each grader container, if the user is also admin
            # skip this as all config has been mounted
            mount_course_config = server_cfg["nbgrader"].get(
                "mount_course_config", False
            )
            if mount_course_config and not admin_user:
                course_cfg_volume_mount = configure_volume_mount(
                    self.course_cfg_volume_name,
                    self.course_cfg_volume_mountpath,
                    os.path.join(self.course_cfg_volume_subpath, course_name),
                    read_only=False,
                )
                if self.course_cfg_volume_name:
                    spawner.log.debug(
                        "Mounting grader course config volume to : %s", username
                    )
                    spawner.volume_mounts.append(course_cfg_volume_mount)

            # set grader environment e.g. uid and gid
            spawner.log.debug(
                "Changing uid and gid for grader: %s to %s %s",
                username,
                self.grader_uid,
                self.grader_gid,
            )
            spawner.environment = {
                "NB_USER": username,
                "NB_UID": f"{self.grader_uid}",
                "NB_GID": f"{self.grader_uid}",
            }

    # set students volume mount
    def configure_student_volumes(
        self,
        spawner,
        nbgrader_cfg,
        course_cfg_list,
        server_mode="teaching",
    ):
        """
        Configure volume mounts for the student
        args:
          spawner: spawner object
          nbgrader_cfg: default nbgrader config
          course_cfg_list: a dictionary containing course config
          server_mode: whether teaching or exam mode, used to differentiate
          home directory location on the nfs server. It's useful when the exam and
          teaching servers are deployed on the same hub.
        """
        selected_profile = spawner.user_options["course_id_slug"]
        course_name, role, course_id = selected_profile.split("+")
        username = spawner.user.name

        course_cfg = course_cfg_list[course_name]["student"][course_id]
        course_members = course_cfg["course_members"]

        if username in course_members:
            # Load grader course config if given
            student_course_cfg = course_cfg["course_config"]

            home_volume_mountpath = f"/home/{username}"
            home_volume_subpath = os.path.join(
                self.home_volume_subpath, server_mode, "students", course_id, username
            )

            home_volume_mount = configure_volume_mount(
                self.home_volume_name, home_volume_mountpath, home_volume_subpath
            )

            spawner.log.debug("Student home volume name is: %s", self.home_volume_name)
            if self.home_volume_name:
                spawner.volume_mounts.append(home_volume_mount)

            # Configure exchange if given in nbgrader_cfg
            exchange_configured = False
            if "default_exchange" in nbgrader_cfg:
                personalized_outbound = nbgrader_cfg["default_exchange"].get(
                    "personalized_outbound", False
                )
                personalized_inbound = nbgrader_cfg["default_exchange"].get(
                    "personalized_inbound", False
                )
                personalized_feedback = nbgrader_cfg["default_exchange"].get(
                    "personalized_feedback", False
                )
                exchange_configured = True

            # Configure exchange if given in course_exchange
            if "course_exchange" in student_course_cfg:
                personalized_outbound = student_course_cfg["course_exchange"].get(
                    "personalized_outbound", False
                )
                personalized_inbound = student_course_cfg["course_exchange"].get(
                    "personalized_inbound", False
                )
                personalized_feedback = student_course_cfg["course_exchange"].get(
                    "personalized_feedback", False
                )
                exchange_configured = True

            # configure exchange volumes if default nbgrader exchange is used
            if exchange_configured:
                spawner.log.debug(
                    "[student][exchange] default exchange for %s %s is given",
                    course_id,
                    username,
                )

                # check whether personalized inbound or outbound enabled
                if personalized_outbound:
                    spawner.log.debug("[outbound] Using personalized outbound")
                    outbound_mount_mountpath = os.path.join(
                        self.nbgrader_exchange_root,
                        course_id,
                        "personalized-outbound",
                        username,
                    )
                    outbound_volume_subpath = os.path.join(
                        self.exchange_volume_subpath,
                        course_name,
                        course_id,
                        "personalized-outbound",
                        username,
                    )

                else:
                    spawner.log.debug("[outbound] Using default outbound")
                    outbound_mount_mountpath = os.path.join(
                        self.nbgrader_exchange_root, course_id, "outbound"
                    )
                    outbound_volume_subpath = os.path.join(
                        self.exchange_volume_subpath, course_name, course_id, "outbound"
                    )

                outbound_volume_mount = configure_volume_mount(
                    self.exchange_volume_name,
                    outbound_mount_mountpath,
                    outbound_volume_subpath,
                    read_only=True,
                )

                # configure inbound
                if personalized_inbound:
                    spawner.log.debug("[inbound] Using personalized inbound directory")
                    inbound_volume_mountpath = os.path.join(
                        self.nbgrader_exchange_root,
                        course_id,
                        "personalized-inbound",
                        username,
                    )
                    inbound_volume_subpath = os.path.join(
                        self.exchange_volume_subpath,
                        course_name,
                        course_id,
                        "personalized-inbound",
                        username,
                    )
                else:
                    spawner.log.debug("[inbound] Using default submit directory")
                    inbound_volume_mountpath = os.path.join(
                        self.nbgrader_exchange_root, course_id, "inbound"
                    )
                    inbound_volume_subpath = os.path.join(
                        self.exchange_volume_subpath, course_name, course_id, "inbound"
                    )

                inbound_volume_mount = configure_volume_mount(
                    self.exchange_volume_name,
                    inbound_volume_mountpath,
                    inbound_volume_subpath,
                )
                # configure feedback
                if personalized_feedback:
                    spawner.log.debug(
                        "[feedback] using personalized feedback directory"
                    )
                    feedback_volume_mountpath = os.path.join(
                        self.nbgrader_exchange_root,
                        course_id,
                        "personalized-feedback",
                        username,
                    )
                    feedback_volume_subpath = os.path.join(
                        self.exchange_volume_subpath,
                        course_name,
                        course_id,
                        "personalized-feedback",
                        username,
                    )
                else:
                    spawner.log.debug("[feedback] using default feedback directory")
                    feedback_volume_mountpath = os.path.join(
                        self.nbgrader_exchange_root, course_id, "feedback"
                    )
                    feedback_volume_subpath = os.path.join(
                        self.exchange_volume_subpath, course_name, course_id, "feedback"
                    )

                feedback_volume_mount = configure_volume_mount(
                    self.exchange_volume_name,
                    feedback_volume_mountpath,
                    feedback_volume_subpath,
                    read_only=True,
                )

                spawner.log.debug(
                    "Student exchange/inbound volume name is: %s",
                    self.exchange_volume_name,
                )

                if self.exchange_volume_name:
                    spawner.volume_mounts.append(outbound_volume_mount)
                    spawner.volume_mounts.append(inbound_volume_mount)
                    spawner.volume_mounts.append(feedback_volume_mount)
                else:
                    spawner.log.warning(
                        "Student exchange volume name is: %s",
                        self.exchange_volume_name,
                        "consult k8s admin to provide the volume for exchange",
                    )
            else:
                spawner.log.warning(
                    "[student][exchange] Default exchange is not configured. "
                    + "Please configure it either using web-based or file-based exchange"
                )

            spawner.log.debug(
                "UID and GID for %s is changed to %s", username, spawner.environment
            )
            spawner.environment = {
                "NB_USER": username,
                "NB_UID": f"{self.student_uid}",
                "NB_GID": f"{self.student_gid}",
            }

    def configure_extra_course_volumes(self, spawner, read_only=True):
        """
        Add extra volume mounts for a particular course (selected profile).
        Public directory /srv/shares/public is always mounted to all courses,
        and is accessible to all users in the hub.
        Whereas private volume mount is only accessible to the registered users.
        args:
          spawner: spawner object
          read_only: whether the vol mounts are read_only to users
        """
        # mount public/common dirs: e.g. instructions and cheatsheets
        public_volume_mountpath = f"{self.extra_volume_mountpath}/public"
        public_volume_subpath = os.path.join(self.share_volume_subpath, "public")

        public_volume_mount = configure_volume_mount(
            self.share_volume_name,
            public_volume_mountpath,
            public_volume_subpath,
            read_only=read_only,
        )

        # course specific shared files / dirs within the selected course
        selected_profile = spawner.user_options["course_id_slug"]
        course_name, role, course_id = selected_profile.split("+")
        username = spawner.user.name

        private_volume_mountpath = f"{self.extra_volume_mountpath}/{course_name}"
        private_volume_subpath = os.path.join(
            self.share_volume_subpath, "courses", "{}".format(course_name)
        )

        private_volume_mount = configure_volume_mount(
            self.share_volume_name,
            private_volume_mountpath,
            private_volume_subpath,
            read_only=read_only,
        )

        spawner.log.debug("Extra volume name is: %s", self.share_volume_name)
        if self.share_volume_name:
            spawner.volume_mounts.append(public_volume_mount)
            spawner.volume_mounts.append(private_volume_mount)
        else:
            spawner.log.warning(
                "Extra volume name is: %s",
                self.share_volume_name,
                "consult k8s admin to provide the volume for exchange",
            )

    def set_extra_volume_mounts(self, spawner, vol_mounts, read_only=True):
        """
        Add extra volume mounts
        args:
          spawner: kubespawner object
          vol_mounts: dictionary of vol mounts to be added to the spawner
          read_only: whether the vol mounts are read_only to users
        """
        # add mount if it does not exists, is it the best way to do?
        # automatically add rw share dir for grader, and ro share for students
        for vmount in vol_mounts["volume_mounts"].values():
            spawner.log.info(
                "Add extra volume mount from config:%s", vmount["mountPath"]
            )
            extra_vmount = configure_volume_mount(
                vmount["name"],
                vmount["mountPath"],
                vmount["subPath"],
                read_only=read_only,
            )
            spawner.volume_mounts.append(extra_vmount)

    def configure_profile_list(self, spawner, server_cfg):
        """
        Configure profile list given server configuration
        args:
            spawner: kubespawner object
            server_cfg: server configuration
        """
        # get course config and its members
        course_cfg_list = get_course_config_and_user(server_cfg)

        nbgrader_cfg = get_nbgrader_cfg(server_cfg)

        # Add default course list to kubespawner profile
        cmds, profile_list, username = self.init_profile_list(spawner, server_cfg)

        if len(course_cfg_list.keys()) > 0:
            grader_profile_list = self.generate_course_profile(
                spawner, server_cfg, nbgrader_cfg, cmds, course_cfg_list, role="grader"
            )
            profile_list.extend(grader_profile_list)

            student_profile_list = self.generate_course_profile(
                spawner, server_cfg, nbgrader_cfg, cmds, course_cfg_list, role="student"
            )
            profile_list.extend(student_profile_list)

        return profile_list

    def configure_pre_spawn_hook(self, spawner, server_cfg):
        """
        Configure pre spawner hook, and update the spawner.
        Home directories for exam users will be separated by semster_id, and course_id
        while assignment users use the same home dir across different courses
        args:
            spawner: kubespawner object
            server_cfg: server configuration
        """
        # Load JupyterHub users (not necessarily have access to coursess)
        # any user file name containing "admin" will be grouped as admin_users
        # allowed_users grouped to allowed_users, as well as blocked_users
        jupyterhub_users = {"allowed_users": [], "blocked_users": [], "admin_users": []}
        if "user_list_path" in server_cfg:
            jupyterhub_users = get_jupyterhub_users(server_cfg)

        # get course config and its members
        course_cfg_list = get_course_config_and_user(server_cfg)

        username = str(spawner.user.name)
        selected_profile = spawner.user_options.get("course_id_slug", "Default")
        spawner.log.info("Selected profile %s", selected_profile)

        # clear spawner attributes as Python spawner objects are peristent
        # if not cleared, they may be persistent across restarts, and
        # result in duplicate mounts resulting in failed startup
        spawner.volume_mounts = []

        # check server mode
        server_mode = server_cfg.get("mode", "teaching")
        spawner.log.debug("Server mode: %s", server_mode)

        admin_user = True if username in jupyterhub_users["admin_users"] else False

        is_grader = True if "grader" in selected_profile else False
        spawner.log.debug("Grader status for user %s is %s", username, is_grader)

        nbgrader_cfg = get_nbgrader_cfg(server_cfg)
        # set grader volume mounts
        if check_consecutive_keys(nbgrader_cfg, "enabled"):
            if is_grader:
                self.configure_grader_volumes(
                    spawner,
                    server_cfg=server_cfg,
                    course_cfg_list=course_cfg_list,
                    admin_user=admin_user,
                )

        # set student volume mounts
        if not is_grader and selected_profile != "Default":
            self.configure_student_volumes(
                spawner, nbgrader_cfg, course_cfg_list, server_mode=server_mode
            )

        # set additional course and extra volume mounts
        if selected_profile != "Default":
            # set extra course volume mounts
            read_only = False if is_grader else True
            self.configure_extra_course_volumes(spawner, read_only=read_only)

            # set extra volume mounts
            if check_consecutive_keys(server_cfg, "extra_mounts", "enabled"):
                if server_cfg["extra_mounts"]["enabled"]:
                    vol_mounts = server_cfg["extra_mounts"]
                    self.configure_extra_volumes(spawner, vol_mounts, read_only)
