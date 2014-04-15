import os
from subprocess import call
import sys

from fabric.api import cd, env, prefix, run

DEPLOYMENTS = {
    'dev': {
        'home': '/var/www/',
        'host_string': 'ubuntu@54.221.204.14',
        'project': 'tally-system',
        'key_filename': os.path.expanduser('~/.ssh/ona.pem'),
        'django_config_module': 'tally_ho.settings.local_settings',
        'pid': '/var/run/tally.pid',
    },
    'prod': {
        'home': '/var/www/',
        'db_host': '192.168.1.1',
        'from_local': True,
        'host_string': 'hnec',  # configure .ssh/config for HNEC
        'project': 'tally-system',
        'django_config_module': 'tally_ho.settings.local_settings',
    }
}


def source(path):
    return prefix('source %s' % path)


def exit_with_error(message):
    print message
    sys.exit(1)


def check_key_filename(deployment_name):
    if 'key_filename' in DEPLOYMENTS[deployment_name] and \
       not os.path.exists(DEPLOYMENTS[deployment_name]['key_filename']):
        exit_with_error("Cannot find required permissions file: %s" %
                        DEPLOYMENTS[deployment_name]['key_filename'])


def setup_env(deployment_name):
    deployment = DEPLOYMENTS.get(deployment_name)

    if deployment is None:
        exit_with_error('Deployment "%s" not found.' % deployment_name)

    env.update(deployment)

    check_key_filename(deployment_name)

    env.virtualenv = os.path.join(env.home, '.virtualenvs',
                                  env.project, 'bin', 'activate')

    env.code_src = os.path.join(env.home, env.project)
    env.pip_requirements_file = os.path.join(env.code_src,
                                             'requirements/common.pip')


def local_deploy():
    env.use_ssh_config = True
    call(['./scripts/deploy'])

    run('rm -rf %s' % env.project)
    run('tar xzvf %s.tgz' % env.project)
    run('mv %s-clean %s' % (env.project, env.project))

    # remove existing deploy and clean new deploy
    run('find %s -name "*.pyc" -exec rm -rf {} \;' % env.project)
    run('find %s -name "._*" -exec rm -rf {} \;' % env.project)
    run('./%s/scripts/install_app %s' % (env.project, env.db_host))


def deploy(deployment_name, branch='master'):
    setup_env(deployment_name)

    if getattr(env, 'from_local', False):
        local_deploy()
        return

    with cd(env.code_src):
        run("git fetch origin")
        run("git checkout origin/%s" % branch)

        run('find . -name "*.pyc" -exec rm -rf {} \;')
        run('find . -name "._" -exec rm -rf {} \;')

    with source(env.virtualenv):
        run("pip install -r %s" % env.pip_requirements_file)

    with cd(env.code_src):
        config_module = env.django_config_module

        with source(env.virtualenv):
            run("python manage.py syncdb --settings=%s" % config_module)
            run("python manage.py migrate --settings=%s" % config_module)
            run("python manage.py collectstatic --settings=%s --noinput"
                % config_module)

    run("sudo /usr/local/bin/uwsgi --reload %s" % env.pid)


def reload_all(deployment_name):
    setup_env(deployment_name)
    with cd(env.code_src):
        with source(env.virtualenv):
            run('./scripts/reload_all tally 127.0.0.1 %s' %
                env.django_config_module)


def manage(deployment_name, cmd):
    setup_env(deployment_name)
    with cd(env.code_src):
        with source(env.virtualenv):
            run('python manage.py %s --settings=%s' %
                (cmd, env.django_config_module))
