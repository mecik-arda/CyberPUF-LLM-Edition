library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity tb_cyberpuf_ust is
end entity tb_cyberpuf_ust;

architecture sim of tb_cyberpuf_ust is

    constant CLK_PERIOD : time := 10 ns;

    signal clk                 : std_logic := '0';
    signal rst                 : std_logic := '1';
    signal komut_anahtar_uret    : std_logic := '0';
    signal komut_sifre_coz_basla   : std_logic := '0';
    signal veri_giris             : std_logic_vector(127 downto 0) := (others => '0');
    signal veri_cikis            : std_logic_vector(127 downto 0);
    signal durum_puf_mesgul     : std_logic;
    signal durum_puf_tamam     : std_logic;
    signal durum_anahtar_gen_mesgul : std_logic;
    signal durum_anahtar_gen_tamam : std_logic;
    signal durum_aes_mesgul     : std_logic;
    signal durum_aes_tamam     : std_logic;
    signal hata_ayiklama_puf_anahtar       : std_logic_vector(255 downto 0);
    signal hata_ayiklama_bit_indeks     : std_logic_vector(8 downto 0);
    signal hata_ayiklama_sayac_a       : std_logic_vector(19 downto 0);
    signal hata_ayiklama_sayac_b       : std_logic_vector(19 downto 0);

    component cyberpuf_ust is
        generic (
            RO_CIFT_SAYISI     : integer := 16;
            INVERTER_SAYISI    : integer := 3;
            SAYICI_GENISLIGI    : integer := 20;
            SAYMA_DONGULERI     : integer := 1000;
            PUF_TEKRARLARI  : integer := 16
        );
        port (
            clk                 : in  std_logic;
            rst                 : in  std_logic;
            komut_anahtar_uret    : in  std_logic;
            komut_sifre_coz_basla   : in  std_logic;
            komut_sifrele_basla     : in  std_logic;
            veri_giris             : in  std_logic_vector(127 downto 0);
            veri_cikis            : out std_logic_vector(127 downto 0);
            durum_anahtar_hazir    : out std_logic;
            durum_puf_mesgul     : out std_logic;
            durum_puf_tamam     : out std_logic;
            durum_anahtar_gen_mesgul : out std_logic;
            durum_anahtar_gen_tamam : out std_logic;
            durum_aes_mesgul     : out std_logic;
            durum_aes_tamam     : out std_logic;
            puf_anahtar_cikis       : out std_logic_vector(255 downto 0);
            hata_ayiklama_bit_indeks     : out std_logic_vector(8 downto 0);
            hata_ayiklama_sayac_a       : out std_logic_vector(19 downto 0);
            hata_ayiklama_sayac_b       : out std_logic_vector(19 downto 0)
        );
    end component;

begin

    clk <= not clk after CLK_PERIOD / 2;

    uut: cyberpuf_ust
        generic map (
            RO_CIFT_SAYISI    => 16,
            INVERTER_SAYISI   => 3,
            SAYICI_GENISLIGI   => 20,
            SAYMA_DONGULERI    => 50,
            PUF_TEKRARLARI => 3
        )
        port map (
            clk                 => clk,
            rst                 => rst,
            komut_anahtar_uret    => komut_anahtar_uret,
            komut_sifre_coz_basla   => komut_sifre_coz_basla,
            komut_sifrele_basla     => '0',
            veri_giris             => veri_giris,
            veri_cikis            => veri_cikis,
            durum_anahtar_hazir    => open,
            durum_puf_mesgul     => durum_puf_mesgul,
            durum_puf_tamam     => durum_puf_tamam,
            durum_anahtar_gen_mesgul => durum_anahtar_gen_mesgul,
            durum_anahtar_gen_tamam => durum_anahtar_gen_tamam,
            durum_aes_mesgul     => durum_aes_mesgul,
            durum_aes_tamam     => durum_aes_tamam,
            puf_anahtar_cikis       => hata_ayiklama_puf_anahtar,
            hata_ayiklama_bit_indeks     => hata_ayiklama_bit_indeks,
            hata_ayiklama_sayac_a       => hata_ayiklama_sayac_a,
            hata_ayiklama_sayac_b       => hata_ayiklama_sayac_b
        );

    process
    begin
        report "========================================";
        report "CyberPUF Top-Level Entegrasyon Testi";
        report "========================================";

        rst <= '1';
        wait for CLK_PERIOD * 10;
        rst <= '0';
        wait for CLK_PERIOD * 5;

        report "ADIM 1: PUF anahtar uretimi baslatiliyor...";
        komut_anahtar_uret <= '1';
        wait for CLK_PERIOD;
        komut_anahtar_uret <= '0';

        wait until durum_anahtar_gen_tamam = '1';
        wait for CLK_PERIOD * 2;

        report "PUF Anahtar uretimi ve key expansion TAMAMLANDI.";
        report "PUF Key: " & to_hstring(hata_ayiklama_puf_anahtar);

        report "ADIM 2: Sifre cozme (decrypt) testi baslatiliyor...";
        veri_giris <= x"00112233445566778899AABBCCDDEEFF";

        komut_sifre_coz_basla <= '1';
        wait for CLK_PERIOD;
        komut_sifre_coz_basla <= '0';

        wait until durum_aes_tamam = '1';
        wait for CLK_PERIOD * 2;

        report "Sifreli Giris : 00112233445566778899AABBCCDDEEFF";
        report "Cozulen Cikis : " & to_hstring(veri_cikis);
        report "Decrypt TAMAMLANDI.";

        report "ADIM 3: Ikinci blok decrypt testi...";
        veri_giris <= x"DEADBEEFCAFEBABE1234567890ABCDEF";

        komut_sifre_coz_basla <= '1';
        wait for CLK_PERIOD;
        komut_sifre_coz_basla <= '0';

        wait until durum_aes_tamam = '1';
        wait for CLK_PERIOD * 2;

        report "Sifreli Giris : DEADBEEFCAFEBABE1234567890ABCDEF";
        report "Cozulen Cikis : " & to_hstring(veri_cikis);
        report "Ikinci blok decrypt TAMAMLANDI.";

        report "ADIM 4: Anahtar yeniden uretimi testi...";
        komut_anahtar_uret <= '1';
        wait for CLK_PERIOD;
        komut_anahtar_uret <= '0';

        wait until durum_anahtar_gen_tamam = '1';
        wait for CLK_PERIOD * 2;

        report "Yeni PUF Key: " & to_hstring(hata_ayiklama_puf_anahtar);
        report "Anahtar yenileme TAMAMLANDI.";

        report "ADIM 5: Yeni anahtarla decrypt testi...";
        veri_giris <= x"AABBCCDD11223344FFEEDDCC99887766";

        komut_sifre_coz_basla <= '1';
        wait for CLK_PERIOD;
        komut_sifre_coz_basla <= '0';

        wait until durum_aes_tamam = '1';
        wait for CLK_PERIOD * 2;

        report "Sifreli Giris : AABBCCDD11223344FFEEDDCC99887766";
        report "Cozulen Cikis : " & to_hstring(veri_cikis);
        report "Yeni anahtarla decrypt TAMAMLANDI.";

        report "========================================";
        report "TUM ENTEGRASYON TESTLERI TAMAMLANDI.";
        report "========================================";

        wait for CLK_PERIOD * 20;
        assert false report "Simulasyon tamamlandi." severity failure;
        wait;
    end process;

end architecture sim;
