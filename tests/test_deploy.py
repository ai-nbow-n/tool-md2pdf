"""Nginx edits must target only the website HTTPS block and be repeatable."""
import unittest
from deploy.configure_nginx import configured_site, INCLUDE


class NginxDeploymentTests(unittest.TestCase):
    def test_only_https_block_is_changed_and_second_install_is_unchanged(self):
        original = '''server {
  server_name unrelated.example;
  listen 443 ssl;
}
server {
  server_name nbow.io www.nbow.io;
  location / { proxy_pass http://localhost:4321; }
  listen 443 ssl;
}
server {
  server_name nbow.io www.nbow.io;
  listen 80;
  return 404;
}
'''
        changed = configured_site(original)
        self.assertEqual(changed.count(INCLUDE), 1)
        self.assertEqual(changed.replace('\n' + INCLUDE, ''), original)
        self.assertNotIn(INCLUDE, changed.split('server {')[3])
        self.assertEqual(configured_site(changed), changed)

    def test_unexpected_layout_fails_without_producing_a_config(self):
        for text in ('server { server_name nbow.io; }',
                     'server {\nserver_name nbow.io www.nbow.io;\nlisten 80;\n}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                configured_site(text)


if __name__ == '__main__':
    unittest.main()
