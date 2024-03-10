Modify nextcloud config to let it work behind keenetic dns
../data/config/config.php

'trusted_domains' =>
  array (
    0 => 'nextcloud.kruchinin.keenetic.pro'
  ),
  'overwritehost' => 'nextcloud.kruchinin.keenetic.pro',


Install 
memories
run command to index
docker exec --user www-data mync php occ memories:index |tee -a memo.log