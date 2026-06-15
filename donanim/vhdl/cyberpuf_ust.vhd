library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity cyberpuf_ust is
    generic (
        RO_CIFT_SAYISI     : integer := 256;
        INVERTER_SAYISI    : integer := 3;
        SAYICI_GENISLIGI    : integer := 20;
        SAYMA_DONGULERI     : integer := 1000;
        PUF_TEKRARLARI  : integer := 15;
        DEBUG_ENABLE    : boolean := true
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
        
        puf_anahtar_cikis   : out std_logic_vector(255 downto 0);

        hata_ayiklama_bit_indeks     : out std_logic_vector(8 downto 0);
        hata_ayiklama_sayac_a       : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
        hata_ayiklama_sayac_b       : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0)
    );
end entity cyberpuf_ust;

architecture rtl of cyberpuf_ust is

    type sistem_durumu_t is (
        SYS_BOSTA,
        SYS_PUF_URETIYOR,
        SYS_PUF_TAMAM,
        SYS_ANAHTAR_GENISLETIYOR,
        SYS_ANAHTAR_TAMAM,
        SYS_HAZIR,
        SYS_SIFRE_COZULUYOR,
        SYS_SIFRE_COZUMU_TAMAM,
        SYS_SIFRELE_BASLA,
        SYS_SIFRELEME_TAMAM
    );
    signal sistem_durumu : sistem_durumu_t;

    signal puf_uret     : std_logic;
    signal puf_anahtar          : std_logic_vector(255 downto 0);
    signal puf_anahtar_gecerli    : std_logic;
    signal puf_mesgul         : std_logic;
    signal puf_bit_indeks    : std_logic_vector(8 downto 0);
    signal puf_ha_sayac_a  : std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
    signal puf_ha_sayac_b  : std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);

    signal anahtar_gen_basla    : std_logic;
    signal anahtar_gen_giris   : std_logic_vector(255 downto 0);
    signal anahtar_gen_tur_anahtarlari : tur_anahtar_dizisi_t;
    signal anahtar_gen_tamam     : std_logic;
    signal anahtar_gen_mesgul     : std_logic;

    signal aes_basla        : std_logic;
    signal aes_sifreli_metin   : std_logic_vector(127 downto 0);
    signal aes_duz_metin    : std_logic_vector(127 downto 0);
    signal aes_tamam         : std_logic;
    signal aes_mesgul         : std_logic;

    signal aes_enc_basla        : std_logic;
    signal aes_enc_duz_metin    : std_logic_vector(127 downto 0);
    signal aes_enc_sifreli_metin : std_logic_vector(127 downto 0);
    signal aes_enc_tamam        : std_logic;
    signal aes_enc_mesgul       : std_logic;

    signal tur_anahtarlari_reg   : tur_anahtar_dizisi_t;
    signal anahtarlar_hazir       : std_logic;

    component puf_anahtar_ureteci is
        generic (
            KEY_WIDTH        : integer := 256;
            RO_CIFT_SAYISI     : integer := 256;
            INVERTER_SAYISI    : integer := 3;
            SAYICI_GENISLIGI    : integer := 20;
            SAYMA_DONGULERI     : integer := 1000;
            REPETITIONS      : integer := 16
        );
        port (
            clk             : in  std_logic;
            rst             : in  std_logic;
            anahtar_uret    : in  std_logic;
            puf_anahtar         : out std_logic_vector(255 downto 0);
            anahtar_gecerli       : out std_logic;
            busy            : out std_logic;
            bit_indeks_cikis   : out std_logic_vector(8 downto 0);
            hata_ayiklama_sayac_a   : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
            hata_ayiklama_sayac_b   : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0)
        );
    end component;

    component aes256_anahtar_genisletme is
        port (
            clk             : in  std_logic;
            rst             : in  std_logic;
            anahtar_giris          : in  std_logic_vector(255 downto 0);
            start           : in  std_logic;
            tur_anahtarlari      : out tur_anahtar_dizisi_t;
            done            : out std_logic;
            busy            : out std_logic
        );
    end component;

    component aes256_sifre_cozme is
        port (
            clk             : in  std_logic;
            rst             : in  std_logic;
            sifreli_metin      : in  std_logic_vector(127 downto 0);
            tur_anahtarlari      : in  tur_anahtar_dizisi_t;
            start           : in  std_logic;
            duz_metin       : out std_logic_vector(127 downto 0);
            done            : out std_logic;
            busy            : out std_logic
        );
    end component;

    component aes256_sifreleyici is
        port (
            clk             : in  std_logic;
            rst             : in  std_logic;
            duz_metin       : in  std_logic_vector(127 downto 0);
            tur_anahtarlari : in  tur_anahtar_dizisi_t;
            start           : in  std_logic;
            sifreli_metin   : out std_logic_vector(127 downto 0);
            done            : out std_logic;
            busy            : out std_logic
        );
    end component;

begin

    puf_gen_inst: puf_anahtar_ureteci
        generic map (
            KEY_WIDTH       => 256,
            RO_CIFT_SAYISI    => RO_CIFT_SAYISI,
            INVERTER_SAYISI   => INVERTER_SAYISI,
            SAYICI_GENISLIGI   => SAYICI_GENISLIGI,
            SAYMA_DONGULERI    => SAYMA_DONGULERI,
            REPETITIONS     => PUF_TEKRARLARI
        )
        port map (
            clk             => clk,
            rst             => rst,
            anahtar_uret    => puf_uret,
            puf_anahtar         => puf_anahtar,
            anahtar_gecerli       => puf_anahtar_gecerli,
            busy            => puf_mesgul,
            bit_indeks_cikis   => puf_bit_indeks,
            hata_ayiklama_sayac_a   => puf_ha_sayac_a,
            hata_ayiklama_sayac_b   => puf_ha_sayac_b
        );

    key_exp_inst: aes256_anahtar_genisletme
        port map (
            clk             => clk,
            rst             => rst,
            anahtar_giris          => anahtar_gen_giris,
            start           => anahtar_gen_basla,
            tur_anahtarlari      => anahtar_gen_tur_anahtarlari,
            done            => anahtar_gen_tamam,
            busy            => anahtar_gen_mesgul
        );

    aes_dec_inst: aes256_sifre_cozme
        port map (
            clk             => clk,
            rst             => rst,
            sifreli_metin      => aes_sifreli_metin,
            tur_anahtarlari      => tur_anahtarlari_reg,
            start           => aes_basla,
            duz_metin       => aes_duz_metin,
            done            => aes_tamam,
            busy            => aes_mesgul
        );

    aes_enc_inst: aes256_sifreleyici
        port map (
            clk             => clk,
            rst             => rst,
            duz_metin       => aes_enc_duz_metin,
            tur_anahtarlari => tur_anahtarlari_reg,
            start           => aes_enc_basla,
            sifreli_metin   => aes_enc_sifreli_metin,
            done            => aes_enc_tamam,
            busy            => aes_enc_mesgul
        );

    durum_anahtar_hazir <= anahtarlar_hazir;

    debug_out_gen: if DEBUG_ENABLE generate
        hata_ayiklama_bit_indeks <= puf_bit_indeks;
        hata_ayiklama_sayac_a <= puf_ha_sayac_a;
        hata_ayiklama_sayac_b <= puf_ha_sayac_b;
        puf_anahtar_cikis <= puf_anahtar;
    end generate debug_out_gen;

    no_debug_out_gen: if not DEBUG_ENABLE generate
        hata_ayiklama_bit_indeks <= (others => '0');
        hata_ayiklama_sayac_a <= (others => '0');
        hata_ayiklama_sayac_b <= (others => '0');
        puf_anahtar_cikis <= (others => '0');
    end generate no_debug_out_gen;

    process(clk, rst)
    begin
        if rst = '1' then
            sistem_durumu <= SYS_BOSTA;
            puf_uret <= '0';
            anahtar_gen_basla <= '0';
            anahtar_gen_giris <= (others => '0');
            aes_basla <= '0';
            aes_sifreli_metin <= (others => '0');
            aes_enc_basla <= '0';
            aes_enc_duz_metin <= (others => '0');
            veri_cikis <= (others => '0');
            durum_puf_mesgul <= '0';
            durum_puf_tamam <= '0';
            durum_anahtar_gen_mesgul <= '0';
            durum_anahtar_gen_tamam <= '0';
            durum_aes_mesgul <= '0';
            durum_aes_tamam <= '0';
            anahtarlar_hazir <= '0';
            for i in 0 to 14 loop
                tur_anahtarlari_reg(i) <= (others => '0');
            end loop;
        elsif rising_edge(clk) then
            puf_uret <= '0';
            anahtar_gen_basla <= '0';
            aes_basla <= '0';
            aes_enc_basla <= '0';
            durum_puf_tamam <= '0';
            durum_anahtar_gen_tamam <= '0';
            durum_aes_tamam <= '0';

            durum_puf_mesgul <= puf_mesgul;
            durum_anahtar_gen_mesgul <= anahtar_gen_mesgul;
            durum_aes_mesgul <= aes_mesgul or aes_enc_mesgul;

            case sistem_durumu is
                when SYS_BOSTA =>
                    if komut_anahtar_uret = '1' then
                        puf_uret <= '1';
                        anahtarlar_hazir <= '0';
                        sistem_durumu <= SYS_PUF_URETIYOR;
                    elsif komut_sifre_coz_basla = '1' and anahtarlar_hazir = '1' then
                        aes_sifreli_metin <= veri_giris;
                        aes_basla <= '1';
                        sistem_durumu <= SYS_SIFRE_COZULUYOR;
                    elsif komut_sifrele_basla = '1' and anahtarlar_hazir = '1' then
                        aes_enc_duz_metin <= veri_giris;
                        aes_enc_basla <= '1';
                        sistem_durumu <= SYS_SIFRELE_BASLA;
                    end if;

                when SYS_PUF_URETIYOR =>
                    if puf_anahtar_gecerli = '1' then
                        durum_puf_tamam <= '1';
                        sistem_durumu <= SYS_PUF_TAMAM;
                    end if;

                when SYS_PUF_TAMAM =>
                    anahtar_gen_giris <= puf_anahtar;
                    anahtar_gen_basla <= '1';
                    sistem_durumu <= SYS_ANAHTAR_GENISLETIYOR;

                when SYS_ANAHTAR_GENISLETIYOR =>
                    if anahtar_gen_tamam = '1' then
                        for i in 0 to 14 loop
                            tur_anahtarlari_reg(i) <= anahtar_gen_tur_anahtarlari(i);
                        end loop;
                        durum_anahtar_gen_tamam <= '1';
                        sistem_durumu <= SYS_ANAHTAR_TAMAM;
                    end if;

                when SYS_ANAHTAR_TAMAM =>
                    anahtar_gen_giris <= (others => '0');
                    anahtarlar_hazir <= '1';
                    sistem_durumu <= SYS_HAZIR;

                when SYS_HAZIR =>
                    if komut_sifre_coz_basla = '1' then
                        aes_sifreli_metin <= veri_giris;
                        aes_basla <= '1';
                        sistem_durumu <= SYS_SIFRE_COZULUYOR;
                    elsif komut_sifrele_basla = '1' then
                        aes_enc_duz_metin <= veri_giris;
                        aes_enc_basla <= '1';
                        sistem_durumu <= SYS_SIFRELE_BASLA;
                    elsif komut_anahtar_uret = '1' then
                        puf_uret <= '1';
                        anahtarlar_hazir <= '0';
                        sistem_durumu <= SYS_PUF_URETIYOR;
                    end if;

                when SYS_SIFRE_COZULUYOR =>
                    if aes_tamam = '1' then
                        veri_cikis <= aes_duz_metin;
                        durum_aes_tamam <= '1';
                        sistem_durumu <= SYS_SIFRE_COZUMU_TAMAM;
                    end if;

                when SYS_SIFRE_COZUMU_TAMAM =>
                    sistem_durumu <= SYS_HAZIR;

                when SYS_SIFRELE_BASLA =>
                    if aes_enc_tamam = '1' then
                        veri_cikis <= aes_enc_sifreli_metin;
                        durum_aes_tamam <= '1';
                        sistem_durumu <= SYS_SIFRELEME_TAMAM;
                    end if;

                when SYS_SIFRELEME_TAMAM =>
                    sistem_durumu <= SYS_HAZIR;

                when others =>
                    sistem_durumu <= SYS_BOSTA;
            end case;
        end if;
    end process;

end architecture rtl;

