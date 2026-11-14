import unittest

from diagnose_discovery import HOST, same_origin_path


class DiscoveryRedirectTests(unittest.TestCase):
    def test_relative_and_default_https_redirects_keep_origin(self):
        self.assertEqual(same_origin_path('/'), '/')
        self.assertEqual(same_origin_path('pf1007l-demo/'), '/pf1007l-demo/')
        self.assertEqual(same_origin_path('pf1007l-test/', '/pf1007l-demo/'),
                         '/pf1007l-demo/pf1007l-test/')
        self.assertEqual(same_origin_path('https://' + HOST + ':443/pf1007l-demo/'),
                         '/pf1007l-demo/')

    def test_no_credentials_follow_redirects_off_the_approved_origin(self):
        for location in ['http://' + HOST + '/', 'https://' + HOST + ':5238/',
                         '//unrelated.example/', 'https://user@' + HOST + '/',
                         'https://@' + HOST + '/', '/?password=anything', '/#fragment']:
            with self.subTest(location=location):
                with self.assertRaisesRegex(RuntimeError, 'approved HTTPS origin'):
                    same_origin_path(location)


if __name__ == '__main__':
    unittest.main()
