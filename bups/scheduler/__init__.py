import anacron
import systemd
import systemd_user

schedulers = {
    "anacron": anacron,
    "systemd": systemd,
    "systemd-user": systemd_user
}
