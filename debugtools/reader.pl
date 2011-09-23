use Data::Dumper;

sub get_cache_handle {
  require Cache::FileCache;

  Cache::FileCache->new
      ({
        namespace => 'BenchmarkService',
        username => 'nobody',
        default_expires_in => '48 hours',
        auto_purge_interval => '240 hours',
       });
}


my $cache = get_cache_handle();
my $data = $cache->get($ARGV[0]);
print "Is data a ref to ARRAY?: ".(ref $data eq "ARRAY"). "\n";

print Dumper($data);
exit;
