from tempo.openstack.common import cfg

CFG = cfg.ConfigOpts(project='tempo', prog='tempo')

cli_opts = [
    cfg.BoolOpt('debug',
                short='d',
                default=False,
                help='Print debugging output')
]

CFG.register_cli_opts(cli_opts)
