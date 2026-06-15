# GHDL compile script
$ghdl_cmd = "ghdl"

Remove-Item -Path "*.cf" -ErrorAction SilentlyContinue

& $ghdl_cmd -a --std=08 vhdl\aes_paket.vhd
& $ghdl_cmd -a --std=08 vhdl\halka_osilator.vhd
& $ghdl_cmd -a --std=08 vhdl\ro_puf_cekirdek.vhd
& $ghdl_cmd -a --std=08 vhdl\puf_anahtar_ureteci.vhd
& $ghdl_cmd -a --std=08 vhdl\aes256_anahtar_genisletme.vhd
& $ghdl_cmd -a --std=08 vhdl\aes256_sifreleyici.vhd
& $ghdl_cmd -a --std=08 vhdl\aes256_sifre_cozme.vhd
& $ghdl_cmd -a --std=08 vhdl\cyberpuf_ust.vhd
& $ghdl_cmd -a --std=08 vhdl\axi4_lite_sarmalayici.vhd
& $ghdl_cmd -a --std=08 testbench\tb_aes256.vhd
& $ghdl_cmd -a --std=08 testbench\tb_cyberpuf_ust.vhd
& $ghdl_cmd -a --std=08 testbench\tb_axi4_lite.vhd

& $ghdl_cmd -m --std=08 tb_aes256
& $ghdl_cmd -m --std=08 tb_cyberpuf_ust
& $ghdl_cmd -m --std=08 tb_axi4_lite

echo "Compilation done!"
