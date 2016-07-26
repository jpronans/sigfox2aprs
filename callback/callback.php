<?php

  $actual_link = "http://$_SERVER[HTTP_HOST]$_SERVER[REQUEST_URI]\r\n";
  $file = 'calls.txt';
  // Open the file to get existing content
  $current = file_get_contents($file);
  // Append the data to the file
  $current .= $actual_link;
  // Write the contents back to the file
  file_put_contents($file, $current);
  // Bare minumum needed for APRS
  $_id = $_GET["id"];
  $_lat = $_GET["lat"];
  $_lng = $_GET["lng"];
  $_data = $_GET["data"];
  
  // Extra information 
  $_time = $_GET["time"];
  $_duplicate = $_GET["duplicate"];
  $_snr = $_GET["snr"];
  $_station = $_GET["station"];
  $_rssi = $_GET["rssi"];
  $_avgSnr = $_GET["avgSnr"];
  $_seqNumber= $_GET["seqNumber"];

  // Based on code from quicksand.be
  // See https://developer.mbed.org/users/quicksand/code/QW-TEMP_GPS-NMEA/shortlog
  // Make sure we have data in the variable before proceeding
  if(isset($_GET["data"])){
    // If its not straight hex data, then exit
    if(!ctype_xdigit($_GET["data"]))
      return false;
    
    $file = "gpsout.txt";
    // Open the file to get existing content
    $current = file_get_contents($file);
  
    // Check for valid GPS data  
    if(substr($_GET["data"],7,12) != "ffffffffffff")
      {
        // Convert it to decimal
        $_preamble = hexdec( substr($_GET["data"],0,2));
	$_gps = hexdec( substr($_GET["data"],7,12));
	$_length = strlen($_gps);

	for($_ctr = $_length; $_ctr < 15; $_ctr++) $_gps = "0".$_gps;
        
        // Get the Symbol for longitude, byte 22, bit 3 / bit 8 of total string
	$longs= substr(sprintf( "%04d", decbin(hexdec( substr($_GET["data"],22,1)))),0,1) == 0 ? "E" : "W";
        // Get the Symbol for latitude, bute 22, bit 2 / bit 7 of total string
	$lats = substr(sprintf( "%04d", decbin(hexdec( substr($_GET["data"],22,1)))),1,1) == 0 ? "N" : "S";
	
        // Get the latitude degrees from the two lefmost bytes of the last 7 in the substring
        $lat_degr = substr($_gps,-7,2);
	// Build an APRS format string DDMM.MMS
	$lat_aprs = sprintf("%02.2d%2.2s.%2.2s%s",$lat_degr,substr($_gps,-5,2),substr($_gps,-3), $lats);
	// Get the longitude from the three leftmost bytes of the gps substring / 
        $lng_degr = substr($_gps,0,3);
        // Build an APRS format string DDHH.MMS 
	$lng_aprs=sprintf("%03.3d"."%2.2s."."%2.2s"."%s",$lng_degr,substr($_gps,3,2),substr($_gps,5,3),$longs);

	// Get the count of satellites visible
        $_satmask = 56; //00111000
        $_satsvar = hexdec(substr($_GET["data"],22,2));
        $_satsraw = $_satsvar & $_satmask;	
	$sats = $_satsraw >> 2;

	// Get the hdop
        $_hdopmask = 3; // 00000011
        $_hdopvar = hexdec(substr($_GET["data"],22,2));
        $hdop = $_hdopmask & $_hdopvar;
	// Write it out
        $_filedata = "Preamble: ".$_preamble.", Lat: " .$lat_aprs. ", Long: ".$lng_aprs. ", Sats: ".$sats.", HDOP: ".$hdop."\r\n";
      
	// Publish to MQTT
	require("phpMQTT/phpMQTT.php");
        $mqtt = new phpMQTT("localhost",1883,"SigFox Publisher");
	if ($mqtt->connect()) {
		//$mqtt->publish("sigfox/".$_id,"id:".$_id,0);
		$mqtt->publish("sigfox/".$_id."/lat",$lat_aprs,0);
		$mqtt->publish("sigfox/".$_id."/lng",$lng_aprs,0);
                $mqtt->publish("sigfox/".$_id."/sats",$sats,0);
                $mqtt->publish("sigfox/".$_id."/hdop",$hdop,0);
		$mqtt->publish("sigfox/aprs",$_id.":".$lat_aprs.":".$lng_aprs.":".$sats.":".$hdop,0);
		// Extra Info, may use for Telemetry later
		$mqtt->publish("sigfox/".$_id."/time",$_time,0);
		$mqtt->publish("sigfox/".$_id."/duplicate",$_duplicate,0);
		$mqtt->publish("sigfox/".$_id."/snr",$_snr,0);
                $mqtt->publish("sigfox/".$_id."/station",$_station,0);
                $mqtt->publish("sigfox/".$_id."/rssi",$_rssi,0);
                $mqtt->publish("sigfox/".$_id."/avgSnr",$_avgSnr,0);
                $mqtt->publish("sigfox/".$_id."/seqNumber",$_seqNumber,0);
		$mqtt->publish("sigfox/telem",$_id.":".$_seqNumber.":".$_snr.":".$_avgSnr.":".$_rssi.":".$sats.":".$hdop,0);


		$mqtt->close();
	}
      }
      else
        {
	  $_filedata = "No GPS fix\r\n";
	}
      // Append the data to the file
      $current .= $_filedata;
      // Write the contents back to the file
      file_put_contents($file, $current);
}
?>
