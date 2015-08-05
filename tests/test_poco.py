#!/usr/bin/env python2

import unittest
import pocketcorr as pc

class TestPOCO(unittest.TestCase):
    def setUp(self):
        self.poco = pc.POCO('localhost')

    def test_ant_ext(self):
        for ant in [4, 8, 16]:
            self.poco.antennas = ant
            antennas = map(self.poco.get_ant_ext, range(self.poco.antennas))
            correct = [chr(ord('a') + i) for i in range(self.poco.antennas)]
            for a, c in zip(antennas, correct):
                self.assertEqual(a, c)

    def test_ant_index(self):
        # Only testing rpoco8 and rpoco16
        bof = 'rpoco8'
        for i in range(8):
            self.assertEqual(pc.get_ant_index(bof, i), i)
            self.assertEqual(pc.get_ant_index(bof, str(i)), i)
            self.assertEqual(pc.get_ant_index(bof, chr(ord('a')+i)), i)
            self.assertEqual(pc.get_ant_index(bof, chr(ord('a')+i)+'1'), i)

        for i in range(32):
            chan = chr(ord('a')+i/4) + str(1+i%4)
            if i % 4:
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, chan)
            if i >= 8:
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, i)
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, str(i))
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, chr(ord('a')+i))

        bof = 'rpoco16'
        for i in range(16):
            chan = chr(ord('a')+i/2) + str(1+i%2)
            self.assertEqual(pc.get_ant_index(bof, chan), i)

        for i in range(32):
            chan = chr(ord('a')+i/4) + str(1+i%4)
            if i % 4 > 1:
                with self.assertRaises(ValueError):
                    pc.get_ant_index(bof, chan)

    def test_get_model(self):
        model_info = {'rpoco8':(1, 8, 'rpoco8.bof'),
                      'rpoco8_r2': (2, 8, 'rpoco8_r2.bof'),
                      'rpoco16': (2, 16, 'rpoco16.bof')}
        for roach in model_info.keys():
            model = model_info[roach][0]
            antennas = model_info[roach][1]
            boffile = model_info[roach][2]
            self.poco.get_model(roach)
            self.assertEqual(self.poco.model, model)
            self.assertEqual(self.poco.antennas, antennas)
            self.assertEqual(self.poco.boffile, boffile)

    def test_xmult_table(self):
        for ant in [4, 8, 16]:
            with open('xmult' + str(ant) + '.csv') as f:
                corrtable = [l[:-1].split(',') for l in f.readlines()]

            # Convert the xmult table to how the get_xmult function outputs.
            xmult = [filter(len, line) for line in corrtable[:ant]]
            xmult = reduce(lambda x, y: x+y, xmult, [])
            index = lambda i: ord(i) - ord('a')
            xmult = [(index(x[0]), index(x[1])) for x in xmult]

            # Get the xmult table using python
            self.poco.antennas = ant
            fst, snd = self.poco.get_xmult()
            xlist = [(min(*x), max(*x)) for x in fst + snd]
            self.assertEqual(sorted(xmult), sorted(xlist))

            # test the mapping between first and second.
            mapping = corrtable[-2:]
            mapping = [[ord(c) - ord('a') for c in m] for m in mapping]
            mapping = dict(zip(*mapping))
            for p1, p2 in zip(fst, snd):
                self.assertEqual((mapping[p1[0]], mapping[p1[1]]), p2)

    def test_set_attributes(self):
        self.poco.model = 1 # not sure why this is needed in the function.
        self.poco.antennas = 8
        self.poco.set_attributes('psa898_v003', 200e6, 2)
        self.assertEqual(self.poco.sdf, -1 * 0.2 / 2 / pc.NCHAN)
        self.assertEqual(self.poco.sfreq, 0.2)

    def test_scheduler(self):
        # not much to do here but check failure cases
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, None, '2000-01-01-00:00')
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, None, None, 'I,10')
        with self.assertRaises(ValueError):
            self.poco.scheduler(None, None, '2000-01-01-00:00', 'I,10')
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, None, '2000-01-01-00:00', 'I,10')
        with self.assertRaises(ValueError):
            self.poco.scheduler(10, '2000-01-01-00:00')
        with self.assertRaises(ValueError):
            self.poco.scheduler(None, '2000-01-01-00:00', '1999-01-01-00:00')

if __name__ == '__main__':
    unittest.main()
