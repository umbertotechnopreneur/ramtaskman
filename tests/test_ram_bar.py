import io
import unittest

from rich.console import Console

from ramtaskman.ram_bar import SystemRamBar, cell_widths
from test_memory import fixture


class RamBarTests(unittest.TestCase):
    def test_bar_uses_all_available_width_without_cap_or_wrapping(self):
        for width in (20, 74, 154, 314):
            with self.subTest(width=width):
                bar = SystemRamBar(fixture().system)
                output = io.StringIO()
                console = Console(file=output, width=width, color_system=None)
                console.print(bar)
                from rich.text import Text
                plain = Text.from_ansi(output.getvalue()).plain.rstrip('\n')
                self.assertEqual(len(plain), width)
                self.assertNotIn('\n', plain)
                self.assertTrue(plain.startswith('RAM  '))
                styles = {str(span.style) for span in bar.render(width).spans}
                self.assertGreater(len(styles), 1)

    def test_tiny_and_zero_parts_do_not_create_or_lose_columns(self):
        values = [999, 1, 0]
        self.assertEqual(cell_widths(values, 1000, 80), [80, 0, 0])
        self.assertEqual(sum(cell_widths([1]*8, 8, 79)), 79)
        self.assertEqual(sum(cell_widths([1]*8, 8, 1)), 1)
        with self.assertRaises(ValueError):
            cell_widths([50, 60], 100, 80)

    def test_legend_keeps_values_too_small_for_a_character(self):
        memory = fixture().system
        memory.segments['anon'] -= 1
        memory.segments['shmem'] += 1
        bar = SystemRamBar(memory)
        self.assertIn('Condivisa/tmpfs', bar.legend().plain)
        self.assertIn('Altro (residuo)', bar.legend().plain)
        self.assertIn('Libera', bar.legend().plain)
        self.assertNotIn('Disponibile', bar.legend().plain)

    def test_fallback_is_explicit_availability_not_a_fake_os_partition(self):
        memory = fixture().system
        memory.segments = {}
        bar = SystemRamBar(memory)
        self.assertFalse(bar.detailed)
        self.assertIn('Disponibile', bar.legend().plain)
        self.assertNotIn('Anonima', bar.legend().plain)
        self.assertEqual(bar.render(80).cell_len, 80)

    def test_wide_localized_labels_keep_bar_width(self):
        memory = fixture().system
        memory.segments = {}
        for language in ('zh', 'ko', 'ja'):
            for width in (20, 80, 160):
                with self.subTest(language=language, width=width):
                    self.assertEqual(SystemRamBar(memory, language).render(width).cell_len, width)
