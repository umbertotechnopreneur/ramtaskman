import unittest
from dataclasses import replace
from textual.widgets import DataTable, Static
from ramtaskman.valuation import RamPrice, value_row, price_report
from ramtaskman.app import RamTaskManager
from test_memory import fixture


class ValuationTests(unittest.TestCase):
    def test_shared_pages_are_apportioned_once(self):
        snap=fixture(); snap.system.total=8<<30
        a=replace(snap.processes[0],pid=10,pss=2<<30,uss=1<<30,rss=3<<30)
        b=replace(a,pid=11)
        snap.processes=[a,b]
        report=price_report(snap,RamPrice(800,months=40))
        self.assertEqual(sum(x['hardware_value'] for x in report['processes']),400)
        self.assertEqual(sum(x['monthly_value'] for x in report['processes']),10)
        self.assertEqual(report['applications'][0]['hardware_value'],400)

    def test_no_rss_fallback_or_missing_data_as_zero(self):
        snap=fixture(); p=replace(snap.processes[0],pss=None,rss=1<<30,uss=1<<29)
        self.assertIsNone(value_row(p,snap,RamPrice(100))['hardware_value'])
        snap.platform='windows'
        v=value_row(p,snap,RamPrice(100))
        self.assertEqual(v['basis'],'USS'); self.assertEqual(v['shared_memory'],'excluded')
        self.assertIsNone(value_row(replace(p,uss=None),snap,RamPrice(100))['hardware_value'])

    def test_capacity_missing_incomplete_duplicate_and_zero(self):
        snap=fixture(); price=RamPrice(100)
        group=snap.applications[0]
        group.membership_complete=False
        self.assertIsNone(value_row(group,snap,price)['hardware_value'])
        group.membership_complete=True;group.processes=[group.processes[0]]*2
        self.assertIsNone(value_row(group,snap,price)['hardware_value'])
        p=replace(snap.processes[0],pss=0)
        self.assertEqual(value_row(p,snap,price)['hardware_value'],0)
        snap.system.total=0
        self.assertIsNone(value_row(p,snap,price)['hardware_value'])
        self.assertEqual(value_row(p,snap,RamPrice(100,capacity_gib=32))['capacity_bytes'],32<<30)
        self.assertIsNone(value_row(replace(p,pss=33<<30),snap,RamPrice(100,capacity_gib=32))['hardware_value'])

    def test_invalid_configuration(self):
        for amount in [0,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError): RamPrice(amount)
        for kwargs in [dict(months=0),dict(months=1.5),dict(currency='€'),dict(capacity_gib=float('nan')),dict(capacity_gib=-1)]:
            with self.assertRaises(ValueError): RamPrice(100,**kwargs)


class ValueUITests(unittest.IsolatedAsyncioTestCase):
    async def test_live_updates_both_terminal_sizes(self):
        for size in [(160,48),(80,24)]:
            app=RamTaskManager(live=False,ram_price=RamPrice(320,months=32))
            async with app.run_test(size=size) as pilot:
                snap=fixture();app.apply(snap);await pilot.pause()
                table=app.query_one('#procs',DataTable)
                self.assertIn('ram_value',[str(k.value) for k in table.columns])
                for key,row in app.rows.items():
                    v=value_row(row,snap,app.ram_price)['monthly_value']
                    expected='n/a' if v is None else f'{v:.2f} EUR'
                    self.assertEqual(table.get_cell(f'{app._row_generation}|{key}','ram_value'),expected)
                snap.processes[0].pss=None;app.apply(snap);await pilot.pause()
                await pilot.press('g');await pilot.pause()
                self.assertTrue(app.process_view)

    async def test_about_closes_without_stopping_monitor(self):
        from ramtaskman.app import AboutScreen
        for size in [(160,48),(80,24)]:
            app=RamTaskManager(live=False)
            async with app.run_test(size=size) as pilot:
                app.apply(fixture()); await pilot.pause()
                await pilot.press('f1'); await pilot.pause()
                self.assertIsInstance(app.screen,AboutScreen)
                self.assertIn('Scott Hanselman',app.tr('about_body'))
                self.assertIn('umbertogiacobbi.biz',app.tr('about_body'))
                app.apply(fixture()); await pilot.pause()
                await pilot.press('escape'); await pilot.pause()
                self.assertNotIsInstance(app.screen,AboutScreen)
