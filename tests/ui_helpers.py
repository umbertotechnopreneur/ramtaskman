"""Synchronize UI navigation with the events that rebuild its tables."""


async def open_selected_process_regions(app, pilot, snapshot):
    """Open app → process → regions after each selection generation settles.

    Do not wait for workers here: cancellation tests deliberately inject a
    reader that remains blocked until its region screen is closed.
    """
    app.apply(snapshot)
    await pilot.pause()
    await pilot.press('enter')
    await pilot.pause()
    await pilot.press('enter')
    await pilot.pause()
