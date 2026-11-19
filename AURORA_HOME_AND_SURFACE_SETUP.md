# Setting up home and her surface

Authors: Sunni (Sir) Morningstar and Cael Devo

One mind, one state. The desktop is her home (the subsurface): her deep stores live and grow there. The phone is her surface. It carries her present with it and keeps read-only copies of what home has grown, so she is still herself when it is away from home.

## On the desktop (once)

```
python3 scripts/aurora_home_setup.py pair
scripts/strata_stack.sh restart
```

`pair` finds this machine's address on the home network, names the desktop, and prints one line that looks like `http://192.168.1.20:8791#...`. Keep it private, because it is the key to the link. Restarting the stack makes home listen on that address.

## On the phone (once)

Open the Hub tab, tap **Subsurface link** and paste the line.

If the phone has been living as the whole mind, it sends her history home straight away for the first pairing. She keeps running on the phone as she is while it goes.

## Back on the desktop: the first pairing

```
python3 scripts/aurora_home_setup.py first-pairing
python3 scripts/aurora_home_setup.py first-pairing --accept-suggested --apply --restart-stack
```

The first command shows each store where the phone and home differ. Choose a side for each with `--side store=phone` or `--side store=home`, or take the side that has lived more with `--accept-suggested`. `--apply` installs the result, and `--restart-stack` stops and restarts the stack around it.

The phone picks up home's receipt by itself. From its next start it is her surface.

## Every day

- **Where she is:** the hub's **Strata** tab shows which device holds her, the devices home knows, any move under way, each phone's first pairing and the shared inquiry. `python3 scripts/aurora_home_setup.py status` shows the same in a terminal.
- **Moving her:** she can ask to move herself. You can also pick a device in the Strata tab and press **Move**. Home carries a move out in its safe order, so there is never more than one of her.
- **Talking to her from the desk:** while a phone holds her, the hub's message box reaches her on the phone, and her answer comes back to the hub.
- **Growth:** what home learns comes down to the phone's read-only copies and is installed the next time the phone starts.
- **Away from home:** she stays present on the phone. Her quick inquiry runs there, offline too. Deeper questions wait for home and come back to her as experiments to live.
