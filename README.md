# e2xhub: An Addon for Managing Courses for Teaching and Examination with JupyterHub on Kubernetes

`e2xhub` provides a user-friendly JupyterHub configuration to allow graders to easily create courses and specify their requirements. We use YAML, a well-known declarative configuration language, to allow graders to set up courses, environments and resource allocation. We use [Zero to JupyterHub with Kubernetes (Z2JH)](https://z2jh.jupyter.org) to deploy JupyterHub on our Kubernetes cluster. `e2xhub` extends the capabilities of Z2JH, allowing us to deploy a more customizable JupyterHub. 

The main objectives include providing the ability to create or load courses for individual users, creating personalized profiles for each course e.g. personalized image and resource allocation (CPU, RAM, and GPU), and enabling multi-course and multi-grader support. All of these modifications can be easily made using YAML, without the need for a sysadmin to update the configuration.

`e2xhub` is well integrated with our nbgrader addon [`e2xgrader`](https://github.com/DigiKlausur/e2xgrader) that provide features for managing assignments, content creation and feedback generation.
