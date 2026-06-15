library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use work.aes_paket.ALL;

entity axi4_lite_sarmalayici is
    generic (
        C_S_AXI_DATA_WIDTH : integer := 32;
        C_S_AXI_ADDR_WIDTH : integer := 8;
        RO_CIFT_SAYISI       : integer := 256;
        INVERTER_SAYISI      : integer := 3;
        SAYICI_GENISLIGI      : integer := 20;
        SAYMA_DONGULERI       : integer := 1000;
        PUF_TEKRARLARI    : integer := 15;
        DEBUG_ENABLE      : boolean := true
    );
    port (
        S_AXI_ACLK     : in  std_logic;
        S_AXI_ARESETN  : in  std_logic;

        S_AXI_AWADDR   : in  std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0);
        S_AXI_AWPROT   : in  std_logic_vector(2 downto 0);
        S_AXI_AWVALID  : in  std_logic;
        S_AXI_AWREADY  : out std_logic;

        S_AXI_WDATA    : in  std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);
        S_AXI_WSTRB    : in  std_logic_vector((C_S_AXI_DATA_WIDTH / 8) - 1 downto 0);
        S_AXI_WVALID   : in  std_logic;
        S_AXI_WREADY   : out std_logic;

        S_AXI_BRESP    : out std_logic_vector(1 downto 0);
        S_AXI_BVALID   : out std_logic;
        S_AXI_BREADY   : in  std_logic;

        S_AXI_ARADDR   : in  std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0);
        S_AXI_ARPROT   : in  std_logic_vector(2 downto 0);
        S_AXI_ARVALID  : in  std_logic;
        S_AXI_ARREADY  : out std_logic;

        S_AXI_RDATA    : out std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);
        S_AXI_RRESP    : out std_logic_vector(1 downto 0);
        S_AXI_RVALID   : out std_logic;
        S_AXI_RREADY   : in  std_logic;

        -- AXI4-Stream Slave (DMA'dan veri alma)
        S_AXIS_TDATA   : in  std_logic_vector(31 downto 0) := (others => '0');
        S_AXIS_TVALID  : in  std_logic := '0';
        S_AXIS_TREADY  : out std_logic;
        S_AXIS_TLAST   : in  std_logic := '0';

        -- AXI4-Stream Master (DMA'ya veri gonderme)
        M_AXIS_TDATA   : out std_logic_vector(31 downto 0);
        M_AXIS_TVALID  : out std_logic;
        M_AXIS_TREADY  : in  std_logic := '0';
        M_AXIS_TLAST   : out std_logic
    );
end entity axi4_lite_sarmalayici;

architecture rtl of axi4_lite_sarmalayici is

    signal axi_awready  : std_logic;
    signal axi_wready   : std_logic;
    signal axi_bresp    : std_logic_vector(1 downto 0);
    signal axi_bvalid   : std_logic;
    signal axi_arready  : std_logic;
    signal axi_rdata    : std_logic_vector(C_S_AXI_DATA_WIDTH - 1 downto 0);
    signal axi_rresp    : std_logic_vector(1 downto 0);
    signal axi_rvalid   : std_logic;

    signal axi_awaddr_latched : std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0);
    signal axi_araddr_latched : std_logic_vector(C_S_AXI_ADDR_WIDTH - 1 downto 0);

    signal aw_en : std_logic;

    signal reg_control     : std_logic_vector(31 downto 0);
    signal reg_status      : std_logic_vector(31 downto 0);
    signal reg_data_in_0   : std_logic_vector(31 downto 0);
    signal reg_data_in_1   : std_logic_vector(31 downto 0);
    signal reg_data_in_2   : std_logic_vector(31 downto 0);
    signal reg_data_in_3   : std_logic_vector(31 downto 0);
    signal reg_data_out_0  : std_logic_vector(31 downto 0);
    signal reg_data_out_1  : std_logic_vector(31 downto 0);
    signal reg_data_out_2  : std_logic_vector(31 downto 0);
    signal reg_data_out_3  : std_logic_vector(31 downto 0);
    signal reg_puf_key_0   : std_logic_vector(31 downto 0);
    signal reg_puf_key_1   : std_logic_vector(31 downto 0);
    signal reg_puf_key_2   : std_logic_vector(31 downto 0);
    signal reg_puf_key_3   : std_logic_vector(31 downto 0);
    signal reg_puf_key_4   : std_logic_vector(31 downto 0);
    signal reg_puf_key_5   : std_logic_vector(31 downto 0);
    signal reg_puf_key_6   : std_logic_vector(31 downto 0);
    signal reg_puf_key_7   : std_logic_vector(31 downto 0);
    signal reg_debug_0     : std_logic_vector(31 downto 0);
    signal reg_debug_1     : std_logic_vector(31 downto 0);

    signal rst_internal    : std_logic;

    signal cmd_generate_key_r : std_logic;
    signal cmd_start_decrypt_r : std_logic;
    signal cmd_start_encrypt_r : std_logic;
    signal cmd_generate_key_pulse : std_logic;
    signal cmd_start_decrypt_pulse : std_logic;
    signal cmd_start_encrypt_pulse : std_logic;

    signal core_data_in     : std_logic_vector(127 downto 0);
    signal core_data_out    : std_logic_vector(127 downto 0);
    signal core_puf_busy    : std_logic;
    signal core_puf_done    : std_logic;
    signal core_kexp_busy   : std_logic;
    signal core_kexp_done   : std_logic;
    signal core_aes_busy    : std_logic;
    signal core_aes_done    : std_logic;
    signal core_puf_key     : std_logic_vector(255 downto 0);
    signal core_bit_index   : std_logic_vector(8 downto 0);
    signal core_count_a     : std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
    signal core_count_b     : std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
    signal core_anahtar_hazir : std_logic;

    signal puf_done_sticky  : std_logic;
    signal kexp_done_sticky : std_logic;
    signal aes_done_sticky  : std_logic;

    -- DMA Stream Sinyalleri
    signal axis_data_buffer : std_logic_vector(127 downto 0);
    signal axis_word_count  : integer range 0 to 3 := 0;
    signal axis_data_ready  : std_logic := '0';
    signal dma_mode_active  : std_logic;
    signal dma_direction    : std_logic;
    signal wait_for_aes     : std_logic := '0';
    
    signal m_axis_word_count : integer range 0 to 3 := 0;
    signal m_axis_valid      : std_logic := '0';
    signal m_axis_data       : std_logic_vector(31 downto 0);
    signal m_axis_sending    : std_logic := '0';
    signal axis_tready_int   : std_logic;

    component cyberpuf_ust is
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
            durum_puf_mesgul     : out std_logic;
            durum_puf_tamam     : out std_logic;
            durum_anahtar_gen_mesgul : out std_logic;
            durum_anahtar_gen_tamam : out std_logic;
            durum_aes_mesgul     : out std_logic;
            durum_aes_tamam     : out std_logic;
            durum_anahtar_hazir    : out std_logic;
            puf_anahtar_cikis   : out std_logic_vector(255 downto 0);
            hata_ayiklama_bit_indeks     : out std_logic_vector(8 downto 0);
            hata_ayiklama_sayac_a       : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0);
            hata_ayiklama_sayac_b       : out std_logic_vector(SAYICI_GENISLIGI - 1 downto 0)
        );
    end component;

begin

    rst_internal <= not S_AXI_ARESETN;
    
    dma_mode_active <= reg_control(5);
    dma_direction <= reg_control(6);

    core_data_in <= axis_data_buffer when dma_mode_active = '1' else
                    reg_data_in_3 & reg_data_in_2 & reg_data_in_1 & reg_data_in_0;

    cyberpuf_core: cyberpuf_ust
        generic map (
            RO_CIFT_SAYISI    => RO_CIFT_SAYISI,
            INVERTER_SAYISI   => INVERTER_SAYISI,
            SAYICI_GENISLIGI   => SAYICI_GENISLIGI,
            SAYMA_DONGULERI    => SAYMA_DONGULERI,
            PUF_TEKRARLARI => PUF_TEKRARLARI,
            DEBUG_ENABLE => DEBUG_ENABLE
        )
        port map (
            clk                 => S_AXI_ACLK,
            rst                 => rst_internal,
            komut_anahtar_uret    => cmd_generate_key_pulse,
            komut_sifre_coz_basla   => cmd_start_decrypt_pulse,
            komut_sifrele_basla     => cmd_start_encrypt_pulse,
            veri_giris             => core_data_in,
            veri_cikis            => core_data_out,
            durum_puf_mesgul     => core_puf_busy,
            durum_puf_tamam     => core_puf_done,
            durum_anahtar_gen_mesgul => core_kexp_busy,
            durum_anahtar_gen_tamam => core_kexp_done,
            durum_aes_mesgul     => core_aes_busy,
            durum_aes_tamam     => core_aes_done,
            durum_anahtar_hazir    => core_anahtar_hazir,
            puf_anahtar_cikis   => core_puf_key,
            hata_ayiklama_bit_indeks     => core_bit_index,
            hata_ayiklama_sayac_a       => core_count_a,
            hata_ayiklama_sayac_b       => core_count_b
        );

    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                cmd_generate_key_r <= '0';
                cmd_start_decrypt_r <= '0';
                cmd_start_encrypt_r <= '0';
            else
                cmd_generate_key_r <= reg_control(0);
                cmd_start_decrypt_r <= reg_control(1);
                cmd_start_encrypt_r <= reg_control(2);
            end if;
        end if;
    end process;

    cmd_generate_key_pulse <= reg_control(0) and (not cmd_generate_key_r);
    cmd_start_encrypt_pulse <= (axis_data_ready and dma_direction) when dma_mode_active = '1' else
                               (reg_control(2) and (not cmd_start_encrypt_r));
    cmd_start_decrypt_pulse <= (axis_data_ready and (not dma_direction)) when dma_mode_active = '1' else 
                               (reg_control(1) and (not cmd_start_decrypt_r));

    -- AXI-Stream Slave (32-bit to 128-bit birleştirme)
    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                axis_word_count <= 0;
                axis_data_buffer <= (others => '0');
                axis_data_ready <= '0';
            else
                axis_data_ready <= '0';
                
                if wait_for_aes = '1' then
                    if core_aes_busy = '1' then
                        wait_for_aes <= '0';
                    end if;
                elsif S_AXIS_TVALID = '1' and axis_tready_int = '1' then
                    if axis_word_count = 0 then
                        axis_data_buffer(31 downto 0) <= S_AXIS_TDATA;
                        axis_word_count <= 1;
                    elsif axis_word_count = 1 then
                        axis_data_buffer(63 downto 32) <= S_AXIS_TDATA;
                        axis_word_count <= 2;
                    elsif axis_word_count = 2 then
                        axis_data_buffer(95 downto 64) <= S_AXIS_TDATA;
                        axis_word_count <= 3;
                    elsif axis_word_count = 3 then
                        axis_data_buffer(127 downto 96) <= S_AXIS_TDATA;
                        axis_word_count <= 0;
                        axis_data_ready <= '1';
                        wait_for_aes <= '1';
                    end if;
                end if;
            end if;
        end if;
    end process;
    axis_tready_int <= '1' when (dma_mode_active = '1' and core_aes_busy = '0' and wait_for_aes = '0' and m_axis_sending = '0' and core_anahtar_hazir = '1') else '0';
    S_AXIS_TREADY <= axis_tready_int;

    -- AXI-Stream Master (128-bit to 32-bit ayrıştırma)
    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                m_axis_word_count <= 0;
                m_axis_valid <= '0';
                m_axis_sending <= '0';
            else
                if core_aes_done = '1' and dma_mode_active = '1' then
                    m_axis_sending <= '1';
                    m_axis_word_count <= 0;
                    m_axis_valid <= '1';
                elsif m_axis_sending = '1' and M_AXIS_TREADY = '1' and m_axis_valid = '1' then
                    if m_axis_word_count = 3 then
                        m_axis_sending <= '0';
                        m_axis_valid <= '0';
                        m_axis_word_count <= 0;
                    else
                        m_axis_word_count <= m_axis_word_count + 1;
                    end if;
                end if;
            end if;
        end if;
    end process;
    
    process(m_axis_word_count, core_data_out)
    begin
        case m_axis_word_count is
            when 0 => m_axis_data <= core_data_out(31 downto 0);
            when 1 => m_axis_data <= core_data_out(63 downto 32);
            when 2 => m_axis_data <= core_data_out(95 downto 64);
            when 3 => m_axis_data <= core_data_out(127 downto 96);
            when others => m_axis_data <= (others => '0');
        end case;
    end process;

    M_AXIS_TDATA <= m_axis_data;
    M_AXIS_TVALID <= m_axis_valid;
    M_AXIS_TLAST <= '1' when m_axis_word_count = 3 else '0';

    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                puf_done_sticky <= '0';
                kexp_done_sticky <= '0';
                aes_done_sticky <= '0';
            else
                if reg_control(4) = '1' then
                    puf_done_sticky <= '0';
                    kexp_done_sticky <= '0';
                    aes_done_sticky <= '0';
                else
                    if core_puf_done = '1' then
                        puf_done_sticky <= '1';
                    end if;
                    if core_kexp_done = '1' then
                        kexp_done_sticky <= '1';
                    end if;
                    if core_aes_done = '1' then
                        aes_done_sticky <= '1';
                    end if;
                end if;
            end if;
        end if;
    end process;

    reg_status(0) <= core_puf_busy;
    reg_status(1) <= puf_done_sticky;
    reg_status(2) <= core_kexp_busy;
    reg_status(3) <= kexp_done_sticky;
    reg_status(4) <= core_aes_busy;
    reg_status(5) <= aes_done_sticky;
    reg_status(31 downto 6) <= (others => '0');

    reg_data_out_0 <= core_data_out(31 downto 0);
    reg_data_out_1 <= core_data_out(63 downto 32);
    reg_data_out_2 <= core_data_out(95 downto 64);
    reg_data_out_3 <= core_data_out(127 downto 96);

    debug_key_gen: if DEBUG_ENABLE generate
        reg_puf_key_0 <= core_puf_key(31 downto 0);
        reg_puf_key_1 <= core_puf_key(63 downto 32);
        reg_puf_key_2 <= core_puf_key(95 downto 64);
        reg_puf_key_3 <= core_puf_key(127 downto 96);
        reg_puf_key_4 <= core_puf_key(159 downto 128);
        reg_puf_key_5 <= core_puf_key(191 downto 160);
        reg_puf_key_6 <= core_puf_key(223 downto 192);
        reg_puf_key_7 <= core_puf_key(255 downto 224);
    end generate debug_key_gen;

    no_debug_key_gen: if not DEBUG_ENABLE generate
        reg_puf_key_0 <= (others => '0');
        reg_puf_key_1 <= (others => '0');
        reg_puf_key_2 <= (others => '0');
        reg_puf_key_3 <= (others => '0');
        reg_puf_key_4 <= (others => '0');
        reg_puf_key_5 <= (others => '0');
        reg_puf_key_6 <= (others => '0');
        reg_puf_key_7 <= (others => '0');
    end generate no_debug_key_gen;

    debug_gen: if DEBUG_ENABLE generate
        reg_debug_0(SAYICI_GENISLIGI - 1 downto 0) <= core_count_a;
        reg_debug_0(31 downto SAYICI_GENISLIGI) <= (others => '0');
        reg_debug_1(SAYICI_GENISLIGI - 1 downto 0) <= core_count_b;
        reg_debug_1(31 downto SAYICI_GENISLIGI) <= (others => '0');
    end generate debug_gen;

    no_debug_gen: if not DEBUG_ENABLE generate
        reg_debug_0 <= (others => '0');
        reg_debug_1 <= (others => '0');
    end generate no_debug_gen;

    S_AXI_AWREADY <= axi_awready;
    S_AXI_WREADY  <= axi_wready;
    S_AXI_BRESP   <= axi_bresp;
    S_AXI_BVALID  <= axi_bvalid;
    S_AXI_ARREADY <= axi_arready;
    S_AXI_RDATA   <= axi_rdata;
    S_AXI_RRESP   <= axi_rresp;
    S_AXI_RVALID  <= axi_rvalid;

    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                axi_awready <= '0';
                aw_en <= '1';
                axi_awaddr_latched <= (others => '0');
            else
                if axi_awready = '0' and S_AXI_AWVALID = '1' and S_AXI_WVALID = '1' and aw_en = '1' then
                    axi_awready <= '1';
                    aw_en <= '0';
                    axi_awaddr_latched <= S_AXI_AWADDR;
                elsif S_AXI_BREADY = '1' and axi_bvalid = '1' then
                    aw_en <= '1';
                    axi_awready <= '0';
                else
                    axi_awready <= '0';
                end if;
            end if;
        end if;
    end process;

    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                axi_wready <= '0';
            else
                if axi_wready = '0' and S_AXI_WVALID = '1' and S_AXI_AWVALID = '1' and aw_en = '1' then
                    axi_wready <= '1';
                else
                    axi_wready <= '0';
                end if;
            end if;
        end if;
    end process;

    process(S_AXI_ACLK)
        variable addr_index : integer;
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                reg_control <= (others => '0');
                reg_data_in_0 <= (others => '0');
                reg_data_in_1 <= (others => '0');
                reg_data_in_2 <= (others => '0');
                reg_data_in_3 <= (others => '0');
            else
                if axi_awready = '1' and S_AXI_AWVALID = '1' and axi_wready = '1' and S_AXI_WVALID = '1' then
                    addr_index := to_integer(unsigned(axi_awaddr_latched(C_S_AXI_ADDR_WIDTH - 1 downto 2)));

                    case addr_index is
                        when 0 =>
                            for byte_idx in 0 to 3 loop
                                if S_AXI_WSTRB(byte_idx) = '1' then
                                    reg_control(byte_idx * 8 + 7 downto byte_idx * 8) <= S_AXI_WDATA(byte_idx * 8 + 7 downto byte_idx * 8);
                                end if;
                            end loop;
                        when 2 =>
                            for byte_idx in 0 to 3 loop
                                if S_AXI_WSTRB(byte_idx) = '1' then
                                    reg_data_in_0(byte_idx * 8 + 7 downto byte_idx * 8) <= S_AXI_WDATA(byte_idx * 8 + 7 downto byte_idx * 8);
                                end if;
                            end loop;
                        when 3 =>
                            for byte_idx in 0 to 3 loop
                                if S_AXI_WSTRB(byte_idx) = '1' then
                                    reg_data_in_1(byte_idx * 8 + 7 downto byte_idx * 8) <= S_AXI_WDATA(byte_idx * 8 + 7 downto byte_idx * 8);
                                end if;
                            end loop;
                        when 4 =>
                            for byte_idx in 0 to 3 loop
                                if S_AXI_WSTRB(byte_idx) = '1' then
                                    reg_data_in_2(byte_idx * 8 + 7 downto byte_idx * 8) <= S_AXI_WDATA(byte_idx * 8 + 7 downto byte_idx * 8);
                                end if;
                            end loop;
                        when 5 =>
                            for byte_idx in 0 to 3 loop
                                if S_AXI_WSTRB(byte_idx) = '1' then
                                    reg_data_in_3(byte_idx * 8 + 7 downto byte_idx * 8) <= S_AXI_WDATA(byte_idx * 8 + 7 downto byte_idx * 8);
                                end if;
                            end loop;
                        when others =>
                            null;
                    end case;
                else
                    if cmd_generate_key_pulse = '1' then
                        reg_control(0) <= '0';
                    end if;
                    if cmd_start_decrypt_pulse = '1' then
                        reg_control(1) <= '0';
                    end if;
                    if cmd_start_encrypt_pulse = '1' then
                        reg_control(2) <= '0';
                    end if;
                    if reg_control(4) = '1' then
                        reg_control(4) <= '0';
                    end if;
                end if;
            end if;
        end if;
    end process;

    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                axi_bvalid <= '0';
                axi_bresp <= "00";
            else
                if axi_awready = '1' and S_AXI_AWVALID = '1' and axi_wready = '1' and S_AXI_WVALID = '1' and axi_bvalid = '0' then
                    axi_bvalid <= '1';
                    axi_bresp <= "00";
                elsif S_AXI_BREADY = '1' and axi_bvalid = '1' then
                    axi_bvalid <= '0';
                end if;
            end if;
        end if;
    end process;

    process(S_AXI_ACLK)
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                axi_arready <= '0';
                axi_araddr_latched <= (others => '0');
            else
                if axi_arready = '0' and S_AXI_ARVALID = '1' then
                    axi_arready <= '1';
                    axi_araddr_latched <= S_AXI_ARADDR;
                else
                    axi_arready <= '0';
                end if;
            end if;
        end if;
    end process;

    process(S_AXI_ACLK)
        variable addr_index : integer;
    begin
        if rising_edge(S_AXI_ACLK) then
            if rst_internal = '1' then
                axi_rvalid <= '0';
                axi_rresp <= "00";
                axi_rdata <= (others => '0');
            else
                if axi_arready = '1' and S_AXI_ARVALID = '1' and axi_rvalid = '0' then
                    axi_rvalid <= '1';
                    axi_rresp <= "00";

                    addr_index := to_integer(unsigned(axi_araddr_latched(C_S_AXI_ADDR_WIDTH - 1 downto 2)));

                    case addr_index is
                        when 0 =>
                            axi_rdata <= reg_control;
                        when 1 =>
                            axi_rdata <= reg_status;
                        when 2 =>
                            axi_rdata <= reg_data_in_0;
                        when 3 =>
                            axi_rdata <= reg_data_in_1;
                        when 4 =>
                            axi_rdata <= reg_data_in_2;
                        when 5 =>
                            axi_rdata <= reg_data_in_3;
                        when 6 =>
                            axi_rdata <= reg_data_out_0;
                        when 7 =>
                            axi_rdata <= reg_data_out_1;
                        when 8 =>
                            axi_rdata <= reg_data_out_2;
                        when 9 =>
                            axi_rdata <= reg_data_out_3;
                        when 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 =>
                            axi_rdata <= (others => '0'); -- GUVENLIK ONLEMI: PUF anahtar okumalari kapatildi
                        when 18 =>
                            axi_rdata <= (others => '0'); -- GUVENLIK ONLEMI: RO sayaci okumalari kapatildi
                        when 19 =>
                            axi_rdata <= (others => '0'); -- GUVENLIK ONLEMI: RO sayaci okumalari kapatildi
                        when others =>
                            axi_rdata <= (others => '0');
                    end case;
                elsif S_AXI_RREADY = '1' and axi_rvalid = '1' then
                    axi_rvalid <= '0';
                end if;
            end if;
        end if;
    end process;

end architecture rtl;
