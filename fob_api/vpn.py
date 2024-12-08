from fob_api import Config, HeadScale
config = Config()

headscale_driver = HeadScale(config.headscale_endpoint, config.headscale_token)
