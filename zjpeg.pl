#! /usr/bin/perl

$targetsize=shift;

if ($targetsize =~ /^([0-9]+)k$/) {
    $targetsize = $1 * 1024;
} elsif ($targetsize =~ /^([0-9]+)m$/) {
    $targetsize = $1 * 1024 * 1024;
}

$geometry=shift;

$targetdir=shift;
$targetdir =~ s:/$::;

print "Target size $targetsize bytes\n";

foreach $original (@ARGV) {
    if ($original =~ m:/:) {
	($dirname, $filename, $filetype) = ($original =~ m:^(.+)/([^/]+)\.([^.]+)$:);
    } else {
	($filename, $filetype) = ($original =~ m:^([^/]+)\.([^.]+)$:);
    }	
    my @oresult = stat $original;
    $originalsize = $oresult[7];

    $justbiggersize = $originalsize;
    $justbiggerquality = 100;

    $justsmallersize = 0;
    $justsmallerquality = 10;

    $quantum = 1;

    my $targetfile = "$targetdir/$filename.jpg";

    my $quality = $justbiggerquality;

    print "Working on $original -> $targetfile\n";

    while (($justbiggerquality - $justsmallerquality) > $quantum) {
	@command = ("convert", "-resize", $geometry, "-quality", $quality, $original, $targetfile);
	system @command;
	@result = stat $targetfile;
	$resultsize = $result[7];

	if ($resultsize > $targetsize) {
	    $justbiggersize = $resultsize;
	    $justbiggerquality = $quality;
	    print "  $quality -> $resultsize is too big\n";
	} else {
	    $justsmallersize = $resultsize;
	    $justsmallerquality = $quality;
	    print "  $quality -> $resultsize is too small\n";
	}
	$quality = int($justsmallerquality + (($justbiggerquality - $justsmallerquality) / 2));
    }
    system "xview $targetfile";
}
