import platform


def get_device_name() -> str:
    platform_name = platform.system()
    match platform_name:
        case 'Windows':
            return 'cpu'
        case 'Linux' | 'Darwin':
            return 'mps'
        case _:
            raise Exception("Unexpected platform name")
