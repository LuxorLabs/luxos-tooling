from luxos import utils


async def fn(ip, port):
    profiles = await utils.rexec(ip, port, "profiles")
    for profile in profiles['PROFILES']:
        if profile['IsTuned']:
            print(f"Restoring tuned profile: {profile['Profile Name']} on IP: {ip}")

if __name__ == '__main__':
    import asyncio

    asyncio.run(fn("10.206.0.58", 4028))

    addresses = utils.load_ips_from_csv("miners.csv", port=4028)
    out = asyncio.run(utils.alaunch(addresses, fn))
    print(out)

rexec(host, port, cmd, parameters, timeout, retry, retry_delay)
->
execute_command(host, port, timeout_sec, cmd, parameters, verbose)
