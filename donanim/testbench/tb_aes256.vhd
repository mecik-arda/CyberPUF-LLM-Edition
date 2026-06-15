library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity tb_aes256 is
end entity tb_aes256;

architecture sim of tb_aes256 is

    constant CLK_PERIOD : time := 10 ns;

    signal clk          : std_logic := '0';
    signal rst          : std_logic := '1';

    signal enc_plaintext  : std_logic_vector(127 downto 0);
    signal enc_round_keys : tur_anahtar_dizisi_t;
    signal enc_start      : std_logic := '0';
    signal enc_ciphertext : std_logic_vector(127 downto 0);
    signal enc_done       : std_logic;
    signal enc_busy       : std_logic;

    signal dec_ciphertext : std_logic_vector(127 downto 0);
    signal dec_round_keys : tur_anahtar_dizisi_t;
    signal dec_start      : std_logic := '0';
    signal dec_plaintext  : std_logic_vector(127 downto 0);
    signal dec_done       : std_logic;
    signal dec_busy       : std_logic;

    signal anahtar_giris         : std_logic_vector(255 downto 0);
    signal key_start      : std_logic := '0';
    signal key_round_keys : tur_anahtar_dizisi_t;
    signal key_done       : std_logic;
    signal key_busy       : std_logic;

    signal test_passed    : boolean := true;

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

    component aes256_sifreleyici is
        port (
            clk             : in  std_logic;
            rst             : in  std_logic;
            duz_metin       : in  std_logic_vector(127 downto 0);
            tur_anahtarlari      : in  tur_anahtar_dizisi_t;
            start           : in  std_logic;
            sifreli_metin      : out std_logic_vector(127 downto 0);
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

begin

    clk <= not clk after CLK_PERIOD / 2;

    key_exp_inst: aes256_anahtar_genisletme
        port map (
            clk        => clk,
            rst        => rst,
            anahtar_giris     => anahtar_giris,
            start      => key_start,
            tur_anahtarlari => key_round_keys,
            done       => key_done,
            busy       => key_busy
        );

    enc_inst: aes256_sifreleyici
        port map (
            clk        => clk,
            rst        => rst,
            duz_metin  => enc_plaintext,
            tur_anahtarlari => enc_round_keys,
            start      => enc_start,
            sifreli_metin => enc_ciphertext,
            done       => enc_done,
            busy       => enc_busy
        );

    dec_inst: aes256_sifre_cozme
        port map (
            clk        => clk,
            rst        => rst,
            sifreli_metin => dec_ciphertext,
            tur_anahtarlari => dec_round_keys,
            start      => dec_start,
            duz_metin  => dec_plaintext,
            done       => dec_done,
            busy       => dec_busy
        );

    process
        variable expected_ct : std_logic_vector(127 downto 0);
    begin
        rst <= '1';
        wait for CLK_PERIOD * 5;
        rst <= '0';
        wait for CLK_PERIOD * 2;

        report "========================================";
        report "TEST 1: NIST AES-256 Key Expansion";
        report "========================================";

        anahtar_giris <= x"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f";
        key_start <= '1';
        wait for CLK_PERIOD;
        key_start <= '0';

        wait until key_done = '1';
        wait for CLK_PERIOD;

        for i in 0 to 14 loop
            enc_round_keys(i) <= key_round_keys(i);
            dec_round_keys(i) <= key_round_keys(i);
        end loop;

        report "Key expansion tamamlandi.";

        report "========================================";
        report "TEST 2: AES-256 Encryption";
        report "========================================";

        enc_plaintext <= x"00112233445566778899aabbccddeeff";
        expected_ct := x"8ea2b7ca516745bfeafc49904b496089";

        enc_start <= '1';
        wait for CLK_PERIOD;
        enc_start <= '0';

        wait until enc_done = '1';
        wait for CLK_PERIOD;

        report "Plaintext  : 00112233445566778899aabbccddeeff";
        report "Ciphertext : " & to_hstring(enc_ciphertext);
        report "Expected   : 8ea2b7ca516745bfeafc49904b496089";

        if enc_ciphertext = expected_ct then
            report "TEST 2 BASARILI: Encryption dogru!";
        else
            report "TEST 2 BASARISIZ: Encryption yanlis!" severity error;
            test_passed <= false;
        end if;

        report "========================================";
        report "TEST 3: AES-256 Decryption";
        report "========================================";

        dec_ciphertext <= enc_ciphertext;

        dec_start <= '1';
        wait for CLK_PERIOD;
        dec_start <= '0';

        wait until dec_done = '1';
        wait for CLK_PERIOD;

        report "Ciphertext  : " & to_hstring(enc_ciphertext);
        report "Decrypted   : " & to_hstring(dec_plaintext);
        report "Expected PT : 00112233445566778899aabbccddeeff";

        if dec_plaintext = x"00112233445566778899aabbccddeeff" then
            report "TEST 3 BASARILI: Decryption dogru!";
        else
            report "TEST 3 BASARISIZ: Decryption yanlis!" severity error;
            test_passed <= false;
        end if;

        report "========================================";
        report "TEST 4: Encrypt-then-Decrypt Round Trip";
        report "========================================";

        enc_plaintext <= x"DEADBEEFCAFEBABE1234567890ABCDEF";
        enc_start <= '1';
        wait for CLK_PERIOD;
        enc_start <= '0';

        wait until enc_done = '1';
        wait for CLK_PERIOD;

        report "Orijinal PT : DEADBEEFCAFEBABE1234567890ABCDEF";
        report "Encrypted   : " & to_hstring(enc_ciphertext);

        dec_ciphertext <= enc_ciphertext;
        dec_start <= '1';
        wait for CLK_PERIOD;
        dec_start <= '0';

        wait until dec_done = '1';
        wait for CLK_PERIOD;

        report "Decrypted   : " & to_hstring(dec_plaintext);

        if dec_plaintext = x"DEADBEEFCAFEBABE1234567890ABCDEF" then
            report "TEST 4 BASARILI: Round-trip dogru!";
        else
            report "TEST 4 BASARISIZ: Round-trip yanlis!" severity error;
            test_passed <= false;
        end if;

        report "========================================";
        report "TEST 5: Farkli Anahtar ile Sifreleme";
        report "========================================";

        anahtar_giris <= x"603DEB1015CA71BE2B73AEF0857D77811F352C073B6108D72D9810A30914DFF4";
        key_start <= '1';
        wait for CLK_PERIOD;
        key_start <= '0';

        wait until key_done = '1';
        wait for CLK_PERIOD;

        for i in 0 to 14 loop
            enc_round_keys(i) <= key_round_keys(i);
            dec_round_keys(i) <= key_round_keys(i);
        end loop;

        enc_plaintext <= x"6BC1BEE22E409F96E93D7E117393172A";
        enc_start <= '1';
        wait for CLK_PERIOD;
        enc_start <= '0';

        wait until enc_done = '1';
        wait for CLK_PERIOD;

        report "Key         : 603DEB10...14DFF4";
        report "Plaintext   : 6BC1BEE22E409F96E93D7E117393172A";
        report "Encrypted   : " & to_hstring(enc_ciphertext);

        dec_ciphertext <= enc_ciphertext;
        dec_start <= '1';
        wait for CLK_PERIOD;
        dec_start <= '0';

        wait until dec_done = '1';
        wait for CLK_PERIOD;

        report "Decrypted   : " & to_hstring(dec_plaintext);

        if dec_plaintext = x"6BC1BEE22E409F96E93D7E117393172A" then
            report "TEST 5 BASARILI: Farkli anahtar round-trip dogru!";
        else
            report "TEST 5 BASARISIZ: Farkli anahtar round-trip yanlis!" severity error;
            test_passed <= false;
        end if;

        report "========================================";
        report "GENEL SONUC";
        report "========================================";

        if test_passed then
            report "TUM TESTLER BASARILI!";
        else
            report "BAZI TESTLER BASARISIZ OLDU!" severity error;
        end if;

        wait for CLK_PERIOD * 10;

        assert false report "Simulasyon tamamlandi." severity failure;
        wait;
    end process;

end architecture sim;
