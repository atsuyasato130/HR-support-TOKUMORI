import { LightningElement, track } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import getGlobalKpiData from '@salesforce/apex/JobOfferKpiController.getGlobalKpiDataWithPeriod';
import getPopulationData from '@salesforce/apex/JobOfferKpiController.getPopulationData';
import getStudentPipelines from '@salesforce/apex/JobOfferKpiController.getStudentPipelines';
import getCANames from '@salesforce/apex/JobOfferKpiController.getCANames';
import updatePipelineStatusAndAccuracy from '@salesforce/apex/JobOfferKpiController.updatePipelineStatusAndAccuracy';
import updatePipelineFields from '@salesforce/apex/JobOfferKpiController.updatePipelineFields';
import updatePipelineFieldsV2 from '@salesforce/apex/JobOfferKpiController.updatePipelineFieldsV2';
import getReferrerKpiData from '@salesforce/apex/JobOfferKpiController.getReferrerKpiData';
import getReferrerKpiDataByAxis from '@salesforce/apex/JobOfferKpiController.getReferrerKpiDataByAxis';
import bulkUpdatePipelineFields from '@salesforce/apex/JobOfferKpiController.bulkUpdatePipelineFields';
import saveAcceptChecklist from '@salesforce/apex/JobOfferKpiController.saveAcceptChecklist';
import getTeamYomiData from '@salesforce/apex/JobOfferKpiController.getTeamYomiData';
import setYomiFlag from '@salesforce/apex/JobOfferKpiController.setYomiFlag';
import updateTeamYomiRow from '@salesforce/apex/JobOfferKpiController.updateTeamYomiRow';
import getConsultantMonthlyRevenue from '@salesforce/apex/JobOfferKpiController.getConsultantMonthlyRevenue';
import setTeamYomiFlag from '@salesforce/apex/JobOfferKpiController.setTeamYomiFlag';
import getCompanyPipelines from '@salesforce/apex/JobOfferKpiController.getCompanyPipelines';
import getCompanyNamesWithActivePipelines from '@salesforce/apex/JobOfferKpiController.getCompanyNamesWithActivePipelines';
import getStudentRevenueCohort from '@salesforce/apex/JobOfferKpiController.getStudentRevenueCohort';

// Phase 3: 送客KPI Apex Imports
import getSoukyakuKpiSummary from '@salesforce/apex/SoukyakuKpiController.getSoukyakuKpiSummary';
import getSoukyakuByCA from '@salesforce/apex/SoukyakuKpiController.getSoukyakuByCA';
import getSoukyakuByEvent from '@salesforce/apex/SoukyakuKpiController.getSoukyakuByEvent';
import getSoukyakuByClient from '@salesforce/apex/SoukyakuKpiController.getSoukyakuByClient';
import getSoukyakuMonthlyTrend from '@salesforce/apex/SoukyakuKpiController.getSoukyakuMonthlyTrend';
import getSoukyakuUnitPriceAnalysis from '@salesforce/apex/SoukyakuKpiController.getSoukyakuUnitPriceAnalysis';
import getSoukyakuNoShow from '@salesforce/apex/SoukyakuKpiController.getSoukyakuNoShow';
import getSoukyakuByCAMonthly from '@salesforce/apex/SoukyakuKpiController.getSoukyakuByCAMonthly';
import getSoukyakuCAList from '@salesforce/apex/SoukyakuKpiController.getSoukyakuCAList';

// 年度は6月始まり
const CURRENT_FY = (() => {
    const now = new Date();
    return now.getMonth() >= 5 ? now.getFullYear() : now.getFullYear() - 1;
})();

const GRAD_YEARS = ['28卒','27卒','26卒','25卒','24卒'];

// 月オプション（6月始まり）
const MONTH_OPTIONS_FY = [
    { label: '全月', value: '' },
    { label: '6月', value: '6' }, { label: '7月', value: '7' }, { label: '8月', value: '8' },
    { label: '9月', value: '9' }, { label: '10月', value: '10' }, { label: '11月', value: '11' },
    { label: '12月', value: '12' }, { label: '1月', value: '1' }, { label: '2月', value: '2' },
    { label: '3月', value: '3' }, { label: '4月', value: '4' }, { label: '5月', value: '5' },
];

const STATUS_OPTIONS = [
    { label: '001.求人紹介', value: '001.求人紹介' },
    { label: '002.説明会参加予定', value: '002.説明会参加予定' },
    { label: '003.説明会参加済み', value: '003.説明会参加済み' },
    { label: '004.説明会参加後辞退', value: '004.説明会参加後辞退' },
    { label: '005.書類選考・適性検査', value: '005.書類選考・適性検査' },
    { label: '006.書類選考・適性検査ＮＧ', value: '006.書類選考・適性検査ＮＧ' },
    { label: '007.書類選考・適性検査後辞退', value: '007.書類選考・適性検査後辞退' },
    { label: '008.一次面接参加予定', value: '008.一次面接参加予定' },
    { label: '009.一次面接通過', value: '009.一次面接通過' },
    { label: '010.一次面接NG', value: '010.一次面接NG' },
    { label: '011.一次面接後辞退', value: '011.一次面接後辞退' },
    { label: '012.二次面接参加予定', value: '012.二次面接参加予定' },
    { label: '013.二次面接通過', value: '013.二次面接通過' },
    { label: '014.二次面接NG', value: '014.二次面接NG' },
    { label: '015.二次面接後辞退', value: '015.二次面接後辞退' },
    { label: '016.三次面接参加予定', value: '016.三次面接参加予定' },
    { label: '017.三次面接通過', value: '017.三次面接通過' },
    { label: '018.三次面接NG', value: '018.三次面接NG' },
    { label: '019.三次面接後辞退', value: '019.三次面接後辞退' },
    { label: '020.最終面接参加予定', value: '020.最終面接参加予定' },
    { label: '021.最終面接通過', value: '021.最終面接通過' },
    { label: '022.最終面接NG', value: '022.最終面接NG' },
    { label: '023.最終面接後辞退', value: '023.最終面接後辞退' },
    { label: '024.内定', value: '024.内定' },
    { label: '025.内定承諾', value: '025.内定承諾' },
    { label: '026.内定後辞退', value: '026.内定後辞退' },
    { label: '027.内定承諾後辞退', value: '027.内定承諾後辞退' },
    { label: '028.飛び', value: '028.飛び' },
];

const ACCURACY_OPTIONS = [
    { label: 'S（100%）', value: 'S' },
    { label: 'A（90%）', value: 'A' },
    { label: 'B（70%）', value: 'B' },
    { label: 'C（40%）', value: 'C' },
];

export default class GlobalKpiDashboard extends NavigationMixin(LightningElement) {
    @track isLoading = true;
    @track isPopLoading = false;
    @track isBynameLoading = false;
    @track _data = null;
    @track _popData = null;
    // Tab6 行データ。再代入のたびに自動でバージョンを進め、bynameKpi のキャッシュ無効化に使う
    @track _bynameRowsData = [];
    _bynameVersion = 0;
    _bynameKpiCache = null;
    _bynameKpiCacheVer = -1;
    get _bynameRows() { return this._bynameRowsData; }
    set _bynameRows(v) { this._bynameRowsData = v; this._bynameVersion++; }
    @track selectedYear = String(CURRENT_FY);
    @track selectedGradYear = '';
    @track selectedMonth = '';
    @track activeTab = 0;
    @track _summaryPeriod = 'all';   // all | h1 | h2 | q1 | q2 | q3 | q4
    @track selectedCA = '';
    @track selectedYomiMonth = '';
    @track selectedPhase = '';
    @track _caNames = [];
    @track _caInputValue = '全CA';   // input表示値（選択名 or 入力中テキスト）
    @track _caSearchText = '';        // フィルタリング用テキスト
    @track _caDropdownOpen = false;

    // Phase 3: 業種切替トグル（紹介/送客）
    @track activeBusinessLine = 'referral';  // 'referral' or 'soukyaku'
    @track isSoukyakuLoading = false;
    @track _soukyakuLoaded = false;
    @track _soukyakuPeriod = 'all';  // all | h1 | h2 | q1 | q2 | q3 | q4
    @track soukyakuSummary = {
        soukyakuCount: 0, attendanceCount: 0, attendanceRate: 0,
        revenue: 0, avgUnitPrice: 0, targetAchievementRate: 0
    };

    get isReferral() { return this.activeBusinessLine === 'referral'; }
    get isSoukyaku() { return this.activeBusinessLine === 'soukyaku'; }
    // 送客件数→着座件数 の突破率（紹介の矢印%と同じ見せ方）。データ0時は「―」
    get soukyakuAttendanceRatePct() {
        const s = this.soukyakuSummary;
        if (!s || !s.soukyakuCount) return '―';
        return (s.attendanceRate || 0) + '%';
    }
    get bizReferralBtnClass() {
        return 'gkd-biz-btn' + (this.isReferral ? ' gkd-biz-btn--active' : '');
    }
    get bizSoukyakuBtnClass() {
        return 'gkd-biz-btn' + (this.isSoukyaku ? ' gkd-biz-btn--active' : '');
    }

    handleBizToggle(event) {
        const line = event.currentTarget.dataset.line;
        if (line === this.activeBusinessLine) return;
        this.activeBusinessLine = line;
        if (line === 'soukyaku') {
            if (!this._soukyakuLoaded) {
                this.loadSoukyakuSummary();
                this._soukyakuLoaded = true;
            }
            // 初期タブ（月別トレンド）のデータも自動ロード
            const fy = this.selectedYear || String(CURRENT_FY);
            const grad = this.selectedGradYear || '';
            const p = this._soukyakuPeriod || 'all';
            if (!this._monthlyLoaded) {
                this._monthlyLoaded = true;
                this.loadSoukyakuMonthly(fy, grad, p);
            }
            // CA一覧も auto-load (combobox 用)
            if (!this._caListLoaded) {
                this._caListLoaded = true;
                this.loadSoukyakuCAList(fy, grad);
            }
        }
    }

    get soukyakuPeriodOptions() {
        const opts = [
            { key: 'all', label: '年度' },
            { key: 'h1',  label: 'H1' },
            { key: 'h2',  label: 'H2' },
            { key: 'q1',  label: 'Q1' },
            { key: 'q2',  label: 'Q2' },
            { key: 'q3',  label: 'Q3' },
            { key: 'q4',  label: 'Q4' },
        ];
        return opts.map(o => ({
            ...o,
            cls: 'gkd-period-btn' + (this._soukyakuPeriod === o.key ? ' gkd-period-btn--active' : '')
        }));
    }

    handleSoukyakuPeriodChange(e) {
        this._soukyakuPeriod = e.currentTarget.dataset.period;
        this._resetSoukyakuTabFlags();
        this.loadSoukyakuSummary();
        this.reloadActiveSoukyakuTab();
    }

    handleSoukyakuCAChange(e) {
        this._selectedSoukyakuCA = e.detail.value || '';
        this._resetSoukyakuTabFlags();
        this.loadSoukyakuSummary();
        this.reloadActiveSoukyakuTab();
    }

    _resetSoukyakuTabFlags() {
        this._caLoaded = false;
        this._eventLoaded = false;
        this._monthlyLoaded = false;
        this._unitPriceLoaded = false;
        this._noShowLoaded = false;
        this._caMonthlyLoaded = false;
        this._clientLoaded = false;
    }

    // 年度・卒年が変わったとき、送客表示中なら送客側も再読込（年度に紐付け）
    _reloadSoukyakuIfActive() {
        if (!this.isSoukyaku) return;
        const fy = this.selectedYear || String(CURRENT_FY);
        const grad = this.selectedGradYear || '';
        this._resetSoukyakuTabFlags();
        this.loadSoukyakuCAList(fy, grad);
        this.loadSoukyakuSummary();
        this.reloadActiveSoukyakuTab();
    }

    reloadActiveSoukyakuTab() {
        const fy = this.selectedYear || String(CURRENT_FY);
        const grad = this.selectedGradYear || '';
        const p = this._soukyakuPeriod || 'all';
        const tab = this.activeSouTab;
        if (tab === 0) {
            this._monthlyLoaded = true;
            this.loadSoukyakuMonthly(fy, grad, p);
        } else if (tab === 1) {
            this._caLoaded = true;
            this.loadSoukyakuByCA(fy, grad, p);
            this._caMonthlyLoaded = true;
            this.loadSoukyakuByCAMonthly(fy, grad);
        } else if (tab === 2) {
            this._eventLoaded = true;
            this.loadSoukyakuByEvent(fy, grad, p);
        } else if (tab === 3) {
            this._noShowLoaded = true;
            this.loadSoukyakuNoShow(fy, grad, p);
        } else if (tab === 4) {
            this._unitPriceLoaded = true;
            this.loadSoukyakuUnitPrice(fy, grad, p);
        } else if (tab === 5) {
            this._clientLoaded = true;
            this.loadSoukyakuByClient(fy, grad, p);
        }
    }

    async loadSoukyakuSummary() {
        this.isSoukyakuLoading = true;
        try {
            const data = await getSoukyakuKpiSummary({
                fy: this.selectedYear || String(CURRENT_FY),
                gradYear: this.selectedGradYear || '',
                period: this._soukyakuPeriod || 'all',
                caName: this._selectedSoukyakuCA || ''
            });
            this.soukyakuSummary = {
                soukyakuCount: data.soukyakuCount || 0,
                attendanceCount: data.attendanceCount || 0,
                attendanceRate: data.attendanceRate || 0,
                revenue: (data.revenue || 0).toLocaleString(),
                avgUnitPrice: (data.avgUnitPrice || 0).toLocaleString(),
                targetAchievementRate: data.targetAchievementRate || 0
            };
        } catch (e) {
            console.error('Soukyaku Summary Error:', e);
            this.dispatchEvent(new ShowToastEvent({
                title: '送客KPI取得エラー',
                message: e?.body?.message || String(e),
                variant: 'error'
            }));
        } finally {
            this.isSoukyakuLoading = false;
        }
    }

    // Phase 4: 送客タブ別 lazy load (ファネル削除済)
    @track isSoukyakuCALoading = false;
    @track isSoukyakuEventLoading = false;
    @track isSoukyakuMonthlyLoading = false;
    @track isSoukyakuUnitPriceLoading = false;
    @track isSoukyakuNoShowLoading = false;
    @track isSoukyakuCAMonthlyLoading = false;
    _caLoaded = false;
    _eventLoaded = false;
    _monthlyLoaded = false;
    _unitPriceLoaded = false;
    _noShowLoaded = false;
    _caMonthlyLoaded = false;
    _caListLoaded = false;
    @track _selectedSoukyakuCA = '';
    @track _soukyakuCAList = [];
    @track soukyakuByCA = [];
    @track soukyakuByEvent = [];
    @track soukyakuByClient = [];
    @track isSoukyakuClientLoading = false;
    _clientLoaded = false;
    @track soukyakuMonthly = null;
    @track soukyakuCountGridLines = [];   // 件数(人数)グラフ共通の縦軸目盛
    @track soukyakuSentBars = [];         // 月別送客人数
    @track soukyakuAttendedBars = [];     // 月別着座人数
    @track soukyakuRevGridLines = [];     // 売上グラフ縦軸目盛(万)
    @track soukyakuRevBars = [];          // 月別売上
    @track soukyakuUnitPrice = null;
    @track soukyakuNoShow = null;
    @track soukyakuByCAMonthly = null;

    get hasSoukyakuByCA() { return Array.isArray(this.soukyakuByCA) && this.soukyakuByCA.length > 0; }
    get hasSoukyakuByEvent() { return Array.isArray(this.soukyakuByEvent) && this.soukyakuByEvent.length > 0; }
    get hasSoukyakuByClient() { return Array.isArray(this.soukyakuByClient) && this.soukyakuByClient.length > 0; }
    get hasSoukyakuMonthly() { return this.soukyakuMonthly && Array.isArray(this.soukyakuMonthly.monthly); }
    get hasSoukyakuNoShow() { return this.soukyakuNoShow && this.soukyakuNoShow.expectedCount > 0; }
    get hasSoukyakuNoShowByCA() { return this.soukyakuNoShow && Array.isArray(this.soukyakuNoShow.byCA) && this.soukyakuNoShow.byCA.length > 0; }
    get hasSoukyakuByCAMonthly() { return this.soukyakuByCAMonthly && Array.isArray(this.soukyakuByCAMonthly.rows) && this.soukyakuByCAMonthly.rows.length > 0; }
    get soukyakuCAOptions() {
        const opts = [{ label: '全員', value: '' }];
        (this._soukyakuCAList || []).forEach(n => opts.push({ label: n, value: n }));
        return opts;
    }

    // 送客タブ管理（紹介と同じ.gkd-tabボタン方式）
    // タブ番号: 0=月別トレンド, 1=担当者別KPI(+ヒートマップ), 2=イベント別KPI, 3=ノーショー分析, 4=単価分析
    @track activeSouTab = 0;
    get isSouTab0() { return this.activeSouTab === 0; }
    get isSouTab1() { return this.activeSouTab === 1; }
    get isSouTab2() { return this.activeSouTab === 2; }
    get isSouTab3() { return this.activeSouTab === 3; }
    get isSouTab4() { return this.activeSouTab === 4; }
    get isSouTab5() { return this.activeSouTab === 5; }
    get souTab0Class() { return 'gkd-tab' + (this.activeSouTab === 0 ? ' gkd-tab-active' : ''); }
    get souTab1Class() { return 'gkd-tab' + (this.activeSouTab === 1 ? ' gkd-tab-active' : ''); }
    get souTab2Class() { return 'gkd-tab' + (this.activeSouTab === 2 ? ' gkd-tab-active' : ''); }
    get souTab3Class() { return 'gkd-tab' + (this.activeSouTab === 3 ? ' gkd-tab-active' : ''); }
    get souTab4Class() { return 'gkd-tab' + (this.activeSouTab === 4 ? ' gkd-tab-active' : ''); }
    get souTab5Class() { return 'gkd-tab' + (this.activeSouTab === 5 ? ' gkd-tab-active' : ''); }

    handleSoukyakuTab(event) {
        const tab = parseInt(event.currentTarget.dataset.tab, 10);
        this.activeSouTab = tab;
        const fy = this.selectedYear || String(CURRENT_FY);
        const grad = this.selectedGradYear || '';
        const p = this._soukyakuPeriod || 'all';
        if (tab === 0 && !this._monthlyLoaded) {
            this._monthlyLoaded = true;
            this.loadSoukyakuMonthly(fy, grad, p);
        } else if (tab === 1) {
            if (!this._caLoaded) {
                this._caLoaded = true;
                this.loadSoukyakuByCA(fy, grad, p);
            }
            if (!this._caMonthlyLoaded) {
                this._caMonthlyLoaded = true;
                this.loadSoukyakuByCAMonthly(fy, grad);
            }
        } else if (tab === 2 && !this._eventLoaded) {
            this._eventLoaded = true;
            this.loadSoukyakuByEvent(fy, grad, p);
        } else if (tab === 3 && !this._noShowLoaded) {
            this._noShowLoaded = true;
            this.loadSoukyakuNoShow(fy, grad, p);
        } else if (tab === 4 && !this._unitPriceLoaded) {
            this._unitPriceLoaded = true;
            this.loadSoukyakuUnitPrice(fy, grad, p);
        } else if (tab === 5 && !this._clientLoaded) {
            this._clientLoaded = true;
            this.loadSoukyakuByClient(fy, grad, p);
        }
    }

    async loadSoukyakuNoShow(fy, grad, period) {
        this.isSoukyakuNoShowLoading = true;
        try {
            const d = await getSoukyakuNoShow({ fy, gradYear: grad, period: period || 'all', caName: this._selectedSoukyakuCA || '' });
            const seg = (rows) => (rows || []).map(r => ({
                key: r.label, label: r.label,
                expectedCount: r.expectedCount, attendedCount: r.attendedCount,
                noShowCount: r.noShowCount, noShowRate: r.noShowRate
            }));
            const diff = d.selDiffPt || 0;
            this.soukyakuNoShow = {
                expectedCount: d.expectedCount || 0,
                attendedCount: d.attendedCount || 0,
                noShowCount: d.noShowCount || 0,
                noShowRate: d.noShowRate || 0,
                lostAmountDisplay: '¥' + Math.round((d.lostAmount || 0) / 10000).toLocaleString() + '万',
                hasSelected: d.hasSelected || false,
                selCaName: d.selCaName,
                selExpectedCount: d.selExpectedCount || 0,
                selNoShowCount: d.selNoShowCount || 0,
                selNoShowRate: d.selNoShowRate || 0,
                selLostAmountDisplay: '¥' + Math.round((d.selLostAmount || 0) / 10000).toLocaleString() + '万',
                selDiffDisplay: (diff > 0 ? '+' : '') + diff + 'pt',
                selDiffClass: diff > 0 ? 'gkd-amber' : (diff < 0 ? 'gkd-green' : ''),
                byRank: seg(d.byRank),
                byDow: seg(d.byDow)
            };
        } catch (e) { console.error('NoShow:', e); }
        finally { this.isSoukyakuNoShowLoading = false; }
    }

    @track _noShowAxis = 'rank';   // rank | dow
    get isNoShowAxisRank() { return this._noShowAxis === 'rank'; }
    get isNoShowAxisDow() { return this._noShowAxis === 'dow'; }
    get noShowAxisRankClass() { return 'gkd-axis-btn' + (this._noShowAxis === 'rank' ? ' gkd-axis-btn--active' : ''); }
    get noShowAxisDowClass() { return 'gkd-axis-btn' + (this._noShowAxis === 'dow' ? ' gkd-axis-btn--active' : ''); }
    get noShowSegRows() {
        if (!this.soukyakuNoShow) return [];
        return this._noShowAxis === 'dow' ? this.soukyakuNoShow.byDow : this.soukyakuNoShow.byRank;
    }
    get noShowSegHeader() { return this._noShowAxis === 'dow' ? '曜日' : '学歴ランク'; }
    get hasNoShowSegRows() { return this.noShowSegRows.length > 0; }
    handleNoShowAxisChange(e) { this._noShowAxis = e.currentTarget.dataset.axis; }

    async loadSoukyakuByCAMonthly(fy, grad) {
        this.isSoukyakuCAMonthlyLoading = true;
        try {
            const data = await getSoukyakuByCAMonthly({ fy, gradYear: grad, caName: this._selectedSoukyakuCA || '' });
            const rawRows = data.rows || [];
            const maxRev = Math.max(...rawRows.map(r => r.totalRevenue || 0), 1);
            // 紹介「個人別月次計上売上」と同じ作り: 担当CA×月次売上＋着座・合計売上・バー
            const rows = rawRows
                .slice()
                .sort((a, b) => (b.totalRevenue || 0) - (a.totalRevenue || 0))
                .map(r => ({
                    caName: r.caName,
                    totalAttendance: r.totalAttendance || 0,
                    totalRevDisplay: '¥' + Math.round((r.totalRevenue || 0) / 10000).toLocaleString() + '万',
                    barStyle: `width:${Math.round(((r.totalRevenue || 0) / maxRev) * 100)}%`,
                    months: (r.monthlyRevenue || []).map((rev, i) => ({
                        key: r.caName + '_' + i,
                        revDisplay: rev > 0 ? Math.round(rev / 10000).toLocaleString() + '万' : '―',
                        cellClass: rev > 0 ? 'gkd-cm-cell gkd-cm-cell--hit' : 'gkd-cm-cell'
                    }))
                }));
            // フッター: 月別の全CA合計
            const totals = [];
            for (let i = 0; i < 12; i++) {
                const sum = rawRows.reduce((acc, r) => acc + ((r.monthlyRevenue && r.monthlyRevenue[i]) || 0), 0);
                totals.push({
                    key: 'tot_' + i,
                    revDisplay: sum > 0 ? Math.round(sum / 10000).toLocaleString() + '万' : '―',
                    cellClass: sum > 0 ? 'gkd-cm-cell gkd-cm-cell--hit' : 'gkd-cm-cell'
                });
            }
            // 合計行の右端: 合計着座・合計売上
            const grandAtt = rawRows.reduce((acc, r) => acc + (r.totalAttendance || 0), 0);
            const grandRev = rawRows.reduce((acc, r) => acc + (r.totalRevenue || 0), 0);
            this.soukyakuByCAMonthly = {
                monthLabels: (data.monthLabels || []).map((l, i) => ({ key: 'ml_' + i, label: l, short: l.substring(5) })),
                rows,
                totals,
                grandAttendance: grandAtt,
                grandRevDisplay: '¥' + Math.round(grandRev / 10000).toLocaleString() + '万'
            };
        } catch (e) { console.error('CAMonthly:', e); }
        finally { this.isSoukyakuCAMonthlyLoading = false; }
    }

    async loadSoukyakuCAList(fy, grad) {
        try {
            const names = await getSoukyakuCAList({ fy, gradYear: grad });
            this._soukyakuCAList = names || [];
        } catch (e) { console.error('CAList:', e); }
    }

    async loadSoukyakuByCA(fy, grad, period) {
        this.isSoukyakuCALoading = true;
        try {
            const rows = await getSoukyakuByCA({ fy, gradYear: grad, period: period || 'all', caName: this._selectedSoukyakuCA || '' });
            this.soukyakuByCA = (rows || []).map(r => ({
                caName: r.caName, soukyakuCount: r.soukyakuCount, attendanceCount: r.attendanceCount,
                attendanceRate: r.attendanceRate,
                avgUnitPriceFormatted: (r.avgUnitPrice || 0).toLocaleString(),
                revenueFormatted: (r.revenue || 0).toLocaleString()
            }));
        } catch (e) { console.error('CA:', e); }
        finally { this.isSoukyakuCALoading = false; }
    }

    async loadSoukyakuByEvent(fy, grad, period) {
        this.isSoukyakuEventLoading = true;
        try {
            const rows = await getSoukyakuByEvent({ fy, gradYear: grad, period: period || 'all', caName: this._selectedSoukyakuCA || '' });
            this.soukyakuByEvent = (rows || []).map(r => ({
                eventId: r.eventId, eventName: r.eventName, companyName: r.companyName,
                status: r.status, soukyakuCount: r.soukyakuCount, attendanceCount: r.attendanceCount,
                attendanceRate: r.attendanceRate,
                avgUnitPriceFormatted: (r.avgUnitPrice || 0).toLocaleString(),
                revenueFormatted: (r.revenue || 0).toLocaleString()
            }));
        } catch (e) { console.error('Event:', e); }
        finally { this.isSoukyakuEventLoading = false; }
    }

    async loadSoukyakuByClient(fy, grad, period) {
        this.isSoukyakuClientLoading = true;
        try {
            const rows = await getSoukyakuByClient({ fy, gradYear: grad, period: period || 'all', caName: this._selectedSoukyakuCA || '' });
            this.soukyakuByClient = (rows || []).map(r => ({
                clientId: r.clientId, clientName: r.clientName,
                eventCount: r.eventCount, soukyakuCount: r.soukyakuCount, attendanceCount: r.attendanceCount,
                attendanceRate: r.attendanceRate,
                avgUnitPriceDisplay: r.avgUnitPrice ? '¥' + (r.avgUnitPrice).toLocaleString() : '―',
                revenueDisplay: r.revenue ? '¥' + Math.round(r.revenue / 10000).toLocaleString() + '万' : '―'
            }));
        } catch (e) { console.error('Client:', e); }
        finally { this.isSoukyakuClientLoading = false; }
    }

    async loadSoukyakuMonthly(fy, grad, period) {
        this.isSoukyakuMonthlyLoading = true;
        try {
            const data = await getSoukyakuMonthlyTrend({ fy, gradYear: grad, period: period || 'all', caName: this._selectedSoukyakuCA || '' });
            const rate = (att, sou) => (sou > 0 ? Math.round((att / sou) * 100) + '%' : '―');
            const monthly = (data.monthly || []).map(r => ({
                label: r.label,
                shortLabel: r.label ? r.label.substring(5) : '',
                soukyakuCount: r.soukyakuCount,
                attendanceCount: r.attendanceCount,
                attendanceRate: rate(r.attendanceCount, r.soukyakuCount),
                revenue: r.revenue || 0,
                revenueDisplay: this._yen10k(r.revenue || 0)
            }));
            const quarterly = (data.quarterly || []).map(r => ({
                label: r.label,
                soukyakuCount: r.soukyakuCount, attendanceCount: r.attendanceCount,
                attendanceRate: rate(r.attendanceCount, r.soukyakuCount),
                revenueDisplay: this._yen10k(r.revenue || 0)
            }));
            const t = data.total || { soukyakuCount: 0, attendanceCount: 0, revenue: 0 };
            const total = {
                soukyakuCount: t.soukyakuCount || 0,
                attendanceCount: t.attendanceCount || 0,
                attendanceRate: rate(t.attendanceCount || 0, t.soukyakuCount || 0),
                revenueDisplay: this._yen10k(t.revenue || 0)
            };
            this.soukyakuMonthly = { monthly, quarterly, total };
            this._computeMonthlyBars(monthly);
        } catch (e) { console.error('Monthly:', e); }
        finally { this.isSoukyakuMonthlyLoading = false; }
    }

    // 円→「○万」表記（小数点なし）
    _yen10k(v) {
        return '¥' + Math.round((v || 0) / 10000).toLocaleString() + '万';
    }

    // 縦軸を丸い数字に切り上げる（上限なし・データ増で自動追従）。{max, step}を返す
    _niceAxis(rawMax, divisions = 4) {
        if (!rawMax || rawMax <= 0) return { max: divisions, step: 1 };
        const rough = rawMax / divisions;
        const mag = Math.pow(10, Math.floor(Math.log10(rough)));
        const norm = rough / mag;
        let niceStep;
        if (norm <= 1) niceStep = 1;
        else if (norm <= 2) niceStep = 2;
        else if (norm <= 5) niceStep = 5;
        else niceStep = 10;
        const step = niceStep * mag;
        return { max: Math.ceil(rawMax / step) * step, step };
    }

    _computeMonthlyBars(monthly) {
        // 紹介トレンドと同じ幾何: viewBox 620x140, 上端y=15 / 下端y=125 / 高さ110, 月ラベルy=136
        const TOP = 15, BOTTOM = 125, H = 110;
        const gap = 565 / 12;
        const bw = Math.max(Math.floor(gap * 0.55), 6);

        const buildGrid = (niceMax, step, fmt) => {
            const lines = [];
            for (let v = 0; v <= niceMax + 0.5; v += step) {
                const y = (TOP + (1 - v / niceMax) * H);
                lines.push({ key: 'g' + v, y: y.toFixed(1), labelY: (y + 3).toFixed(1), label: fmt(v) });
            }
            return lines;
        };
        const buildBars = (accessor, niceMax, revFmt) => monthly.map((m, idx) => {
            const v = accessor(m) || 0;
            const h = v > 0 ? Math.max((v / niceMax) * H, 2) : 0;
            const x = 44 + idx * gap + (gap - bw) / 2;
            const y = BOTTOM - h;
            return {
                key: 'b' + idx, x: x.toFixed(1), y: y.toFixed(1),
                width: bw, height: h.toFixed(1),
                centerX: (x + bw / 2).toFixed(1), countY: (y - 3).toFixed(1),
                value: v, hasVal: v > 0,
                valLabel: revFmt ? revFmt(v) : String(v),
                label: m.shortLabel
            };
        });

        // 件数（人数）2グラフは共通の縦軸（送客人数の最大に合わせる＝送客≧着座なので両方収まる）
        const countMax = Math.max(...monthly.map(m => m.soukyakuCount || 0), 0);
        const ca = this._niceAxis(countMax);
        this.soukyakuCountGridLines = buildGrid(ca.max, ca.step, v => String(v));
        this.soukyakuSentBars = buildBars(m => m.soukyakuCount, ca.max, null);
        this.soukyakuAttendedBars = buildBars(m => m.attendanceCount, ca.max, null);

        // 売上グラフ（万表記）
        const revMax = Math.max(...monthly.map(m => m.revenue || 0), 0);
        const ra = this._niceAxis(revMax);
        this.soukyakuRevGridLines = buildGrid(ra.max, ra.step, v => Math.round(v / 10000).toLocaleString() + '万');
        this.soukyakuRevBars = buildBars(m => m.revenue, ra.max, v => '¥' + Math.round(v / 10000).toLocaleString() + '万');
    }

    async loadSoukyakuUnitPrice(fy, grad, period) {
        this.isSoukyakuUnitPriceLoading = true;
        try {
            this.soukyakuUnitPrice = await getSoukyakuUnitPriceAnalysis({ fy, gradYear: grad, period: period || 'all' });
        } catch (e) { console.error('UnitPrice:', e); }
        finally { this.isSoukyakuUnitPriceLoading = false; }
    }

    @track _showDetailModal = false;
    @track _detailPipelineId = null;
    @track _checklistState = {};
    // Tab7: チームヨミ管理
    @track _teamYomiRows = [];
    @track _isTeamYomiLoading = false;
    // Tab8: 個人別月次
    @track _consultantMonthlyData = null;
    @track _isConsultantMonthlyLoading = false;
    @track _showCmDetailModal = false;
    @track _cmDetailCa = null;
    @track _cmDetailMonthIdx = null;
    @track _teamYomiEditMap = {};   // pipelineId → 編集中フィールド値
    @track _selectedTeamYomiMonth = '';
    @track _selectedTeamYomiCA = '';
    // Tab6: 一括操作（チェックボックス選択・一括適用ツールバー）
    @track _selectedRowIds = [];
    @track _bulkStatus = '';
    @track _bulkAccuracy = '';
    @track _bulkYomiMonth = '';
    @track _isBulkApplying = false;
    // Tab6: ソート（面談日が新しい順がデフォルト）
    @track _sortField = 'meetingDate';
    @track _sortDir = 'desc';
    @track _companyQuery = '';
    @track _selectedAccuracyFilter = '';
    // Tab6: 非アクティブ学生（時期追い・連絡なし）の表示トグル
    @track _showInactive = false;
    // Tab6: ヨミチェック（YomiFlag__c）のみに絞り込むトグル
    @track _onlyYomiFlag = false;
    // Tab6: 学生名による絞り込み（部分一致）
    @track _studentNameQuery = '';
    // Tab8: 企業別進捗管理
    @track _companyTabRows = [];
    @track _companyTabQuery = '';
    @track _companyTabCA = '';        // Tab8専用 担当CA フィルタ（上部とは独立）
    @track _companyTabGradYear = '';  // Tab8専用 卒年フィルタ
    @track _companyTabPhase = '';     // Tab8専用 選考フェーズフィルタ（client-side）
    @track _isCompanyTabLoading = false;
    @track _companyNames = [];
    @track _companyDropdownOpen = false;
    // Tab9: 学生別売上コホート
    @track _studentCohortRows = [];
    @track _isCohortLoading = false;
    @track _cohortQuery = '';
    @track _cohortShowAll = false;   // デフォルト: 売上ゼロ・紹介ゼロ学生は非表示
    @track _cohortBasis = 'referral'; // 'referral' = 紹介月ベース / 'accept' = 承諾月ベース
    // Tab5: 紹介者別 KPI
    @track _referrerRows = [];
    @track _isReferrerLoading = false;
    @track _referrerAxis = 'reporter';  // 'reporter'(ReportPerson__c) or 'route'(ApplicationRoute__pc)

    get yearOptions() {
        const opts = [{ label: '全期間', value: '' }];
        for (let y = CURRENT_FY; y >= CURRENT_FY - 4; y--) opts.push({ label: `${y}年度`, value: String(y) });
        return opts;
    }
    get gradYearOptions() {
        const opts = [{ label: '全卒年', value: '' }];
        GRAD_YEARS.forEach(y => opts.push({ label: y, value: y }));
        return opts;
    }
    get monthOptions() { return MONTH_OPTIONS_FY; }

    // 上部フィルタ（年度6月始まり + 月）から「YYYY-MM」を導出する。
    // - 月未選択時は null
    // - 6〜12月: カレンダー年 = selectedYear
    // - 1〜5月:  カレンダー年 = selectedYear + 1
    _derivedYomiMonthFromHeader() {
        if (!this.selectedYear || !this.selectedMonth) return null;
        const fy = parseInt(this.selectedYear, 10);
        const m  = parseInt(this.selectedMonth, 10);
        if (isNaN(fy) || isNaN(m)) return null;
        const calendarYear = (m >= 6) ? fy : fy + 1;
        const mm = String(m).padStart(2, '0');
        return `${calendarYear}-${mm}`;
    }
    // Tab6/Tab7 で使う実効ヨミ月: タブ独自フィルタ優先・なければ上部共通から導出
    _effectiveYomiMonth(localOverride) {
        return localOverride || this._derivedYomiMonthFromHeader();
    }
    get caOptions() {
        const opts = [{ label: '全CA', value: '' }];
        this._caNames.forEach(n => opts.push({ label: n, value: n }));
        return opts;
    }
    get filteredCAOptions() {
        const q = (this._caSearchText || '').toLowerCase();
        const all = [{ label: '全CA', value: '', itemClass: 'gkd-ca-item' + (this.selectedCA === '' ? ' gkd-ca-item-selected' : '') }];
        this._caNames
            .filter(n => !q || n.toLowerCase().includes(q))
            .forEach(n => all.push({
                label: n, value: n,
                itemClass: 'gkd-ca-item' + (this.selectedCA === n ? ' gkd-ca-item-selected' : '')
            }));
        return all;
    }
    get caInputValue() { return this._caInputValue; }
    get phaseOptions() {
        return [
            { label: '全フェーズ', value: '' },
            { label: '説明会', value: 'session' },
            { label: '書類選考', value: 'screening' },
            { label: '一次面接', value: 'interview1' },
            { label: '二次面接', value: 'interview2' },
            { label: '三次面接', value: 'interview3' },
            { label: '最終面接', value: 'final' },
            { label: '内定・承諾', value: 'offer' },
        ];
    }
    _phaseStatusMap = {
        session:    ['002.説明会参加予定', '003.説明会参加済み'],
        screening:  ['005.書類選考・適性検査'],
        interview1: ['008.一次面接参加予定', '009.一次面接通過'],
        interview2: ['012.二次面接参加予定', '013.二次面接通過'],
        interview3: ['016.三次面接参加予定', '017.三次面接通過'],
        final:      ['020.最終面接参加予定', '021.最終面接通過'],
        offer:      ['024.内定', '025.内定承諾'],
    };
    get statusOptions() { return STATUS_OPTIONS; }
    get accuracyOptions() { return ACCURACY_OPTIONS; }

    // Tab6 編集用 共有静的options（全行で1本を使い回す。<select value> でselected反映）
    get accuracyEditOptions() { return [{ label: '―', value: '' }, ...ACCURACY_OPTIONS]; }
    get yomiMonthEditOptions() {
        if (!this._yomiMonthEditOptionsCache) {
            const opts = [{ label: '―', value: '' }];
            const now = new Date();
            for (let i = -11; i <= 3; i++) {
                const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
                const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
                opts.push({ label: `${d.getFullYear()}/${d.getMonth() + 1}月`, value: val });
            }
            this._yomiMonthEditOptionsCache = opts;
        }
        return this._yomiMonthEditOptionsCache;
    }

    // #P10: ヨミ月オプション（直近12ヶ月 + 翌3ヶ月）
    get yomiMonthOptions() {
        const opts = [{ label: '全月', value: '' }];
        const now = new Date();
        for (let i = -11; i <= 3; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
            const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            opts.push({ label: `${d.getFullYear()}/${d.getMonth() + 1}月`, value: val });
        }
        return opts;
    }

    get isTab0() { return this.activeTab === 0; }
    get isTab1() { return this.activeTab === 1; }
    get isTab2() { return this.activeTab === 2; }
    get isTab3() { return this.activeTab === 3; }
    get isTab4() { return this.activeTab === 4; }
    get isTab6() { return this.activeTab === 6; }

    get tab0Class() { return `gkd-tab${this.activeTab === 0 ? ' gkd-tab-active' : ''}`; }
    get tab1Class() { return `gkd-tab${this.activeTab === 1 ? ' gkd-tab-active' : ''}`; }
    get tab2Class() { return `gkd-tab${this.activeTab === 2 ? ' gkd-tab-active' : ''}`; }
    get tab3Class() { return `gkd-tab${this.activeTab === 3 ? ' gkd-tab-active' : ''}`; }
    get tab4Class() { return `gkd-tab${this.activeTab === 4 ? ' gkd-tab-active' : ''}`; }
    get tab6Class() { return `gkd-tab${this.activeTab === 6 ? ' gkd-tab-active' : ''}`; }
    get isTab8() { return this.activeTab === 8; }
    get tab8Class() { return `gkd-tab${this.activeTab === 8 ? ' gkd-tab-active' : ''}`; }
    get isTab9() { return this.activeTab === 9; }
    get tab9Class() { return `gkd-tab${this.activeTab === 9 ? ' gkd-tab-active' : ''}`; }
    get isTab5() { return this.activeTab === 5; }
    get tab5Class() { return `gkd-tab${this.activeTab === 5 ? ' gkd-tab-active' : ''}`; }

    connectedCallback() {
        // Tab7（チームヨミ管理）のデフォルトを「今月」に明示セット
        // → Apex側のfiscalYear範囲バグ（4月〜3月固定）回避＋デフォルトで今月の数値を確実に表示
        const now = new Date();
        this._selectedTeamYomiMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

        this.loadMain();
        this.loadCANames();
    }

    _resetSubData() {
        this._popData = null;
        this._consultantMonthlyData = null;
    }

    handleYearChange(e) {
        this.selectedYear = e.detail.value;
        this.selectedMonth = '';
        this._resetSubData();
        this._studentCohortRows = [];   // 常にクリア（次にTab9を開いた時に再ロード）
        this._referrerRows = [];
        this.loadMain();
        if (this.activeTab === 4) this.loadPopulation();
        if (this.activeTab === 5) this.loadReferrerKpi();
        if (this.activeTab === 6) { this._bynameRows = []; this.loadByname(); }
        if (this.activeTab === 7) { this._teamYomiRows = []; this.loadTeamYomi(); }
        if (this.activeTab === 9) this.loadStudentCohort();
        this._reloadSoukyakuIfActive();
    }
    handleGradYearChange(e) {
        this.selectedGradYear = e.detail.value;
        this._resetSubData();
        this._bynameRows = [];
        this._studentCohortRows = [];
        this._referrerRows = [];
        this.loadMain();
        if (this.activeTab === 4) this.loadPopulation();
        if (this.activeTab === 5) this.loadReferrerKpi();
        if (this.activeTab === 6) this.loadByname();
        if (this.activeTab === 9) this.loadStudentCohort();
        this._reloadSoukyakuIfActive();
    }
    handleMonthChange(e) {
        this.selectedMonth = e.detail.value;
        this._referrerRows = [];
        this.loadMain();
        if (this.activeTab === 4) this.loadPopulation();
        if (this.activeTab === 5) this.loadReferrerKpi();
        if (this.activeTab === 6) { this._bynameRows = []; this.loadByname(); }
        if (this.activeTab === 7) { this._teamYomiRows = []; this.loadTeamYomi(); }
    }
    handleTab(e) {
        const tab = parseInt(e.currentTarget.dataset.tab, 10);
        this.activeTab = tab;
        if (tab === 4 && !this._popData) this.loadPopulation();
        if (tab === 6 && this._bynameRows.length === 0) this.loadByname();
        if (tab === 7 && this._teamYomiRows.length === 0) this.loadTeamYomi();
        if (tab === 2 && this._consultantMonthlyData === null) this.loadConsultantMonthly();
        if (tab === 8 && this._companyTabQuery.length >= 3 && this._companyTabRows.length === 0) this.loadCompanyTab();
        if (tab === 8 && this._companyNames.length === 0) this.loadCompanyNames();
        if (tab === 9 && this._studentCohortRows.length === 0) this.loadStudentCohort();
        if (tab === 5 && this._referrerRows.length === 0) this.loadReferrerKpi();
    }

    async loadReferrerKpi() {
        this._isReferrerLoading = true;
        try {
            this._referrerRows = await getReferrerKpiDataByAxis({
                fiscalYear: this.selectedYear || null,
                gradYear:   this.selectedGradYear || null,
                selectedMonth: this.selectedMonth || null,
                period: this._summaryPeriod || null,
                axis: this._referrerAxis || 'reporter'
            });
        } catch (e) { this.showError(e); }
        finally { this._isReferrerLoading = false; }
    }
    handleReferrerAxisChange(e) {
        this._referrerAxis = e.target.dataset.axis;
        this._referrerRows = [];
        this.loadReferrerKpi();
    }
    get isReferrerAxisReporter() { return this._referrerAxis === 'reporter'; }
    get isReferrerAxisRoute() { return this._referrerAxis === 'route'; }
    get referrerAxisReporterClass() { return this._referrerAxis === 'reporter' ? 'gkd-axis-btn gkd-axis-btn--active' : 'gkd-axis-btn'; }
    get referrerAxisRouteClass() { return this._referrerAxis === 'route' ? 'gkd-axis-btn gkd-axis-btn--active' : 'gkd-axis-btn'; }
    get referrerAxisLabel() {
        return this._referrerAxis === 'route' ? '応募経路' : '紹介者';
    }

    get hasReferrerRows() { return this._referrerRows && this._referrerRows.length > 0; }

    // 表示用整形（金額フォーマット等）
    get processedReferrerRows() {
        const fmt = v => '¥' + Number(Math.round(v || 0)).toLocaleString();
        return this._referrerRows.map(r => ({
            ...r,
            avgAcceptPriceDisplay: r.accepted > 0 ? fmt(r.avgAcceptPrice) : '―',
            revenueDisplay: fmt(r.revenue),
            bookedRevenueDisplay: fmt(r.bookedRevenue),
            weightedYomiDisplay: fmt(r.weightedYomi)
        }));
    }

    // 紹介者別ファネル合計（歩留まり表示用）
    get referrerFunnel() {
        if (!this._referrerRows.length) return null;
        const sum = (key) => this._referrerRows.reduce((s, r) => s + (r[key] || 0), 0);
        const interviewed = sum('interviewedStudents');
        const referred = sum('referredStudents');
        const session = sum('sessionParticipated');
        const offers = sum('offerCount');
        const accepted = sum('accepted');
        const pct = (n, d) => d > 0 ? (n / d * 100).toFixed(1) + '%' : '―';
        return {
            interviewed, referred, session, offers, accepted,
            refRate: pct(referred, interviewed),
            sessionRate: pct(session, referred),
            offerRate: pct(offers, session),
            acceptRate: pct(accepted, offers),
            totalAcceptRate: pct(accepted, interviewed)
        };
    }

    async loadStudentCohort() {
        this._isCohortLoading = true;
        try {
            this._studentCohortRows = await getStudentRevenueCohort({
                fiscalYear: this.selectedYear || null,
                caName: this.selectedCA || null,
                gradYear: this.selectedGradYear || null
            });
        } catch (e) { this.showError(e); }
        finally { this._isCohortLoading = false; }
    }

    handleCohortQueryInput(e) {
        this._cohortQuery = e.target.value || '';
    }
    handleCohortShowAllToggle(e) {
        this._cohortShowAll = e.target.checked;
    }
    handleCohortCAChange(e) {
        this.selectedCA = e.detail.value;
        this._caInputValue = this.selectedCA || '全CA';
        this._studentCohortRows = [];
        this.loadStudentCohort();
    }

    get studentCohortRows() {
        if (!this._studentCohortRows.length) return [];
        const qStripped = (this._cohortQuery || '').replace(/[\s　]+/g, '').toLowerCase();
        let rows = this._studentCohortRows;
        if (!this._cohortShowAll) {
            rows = rows.filter(r => (r.realRevenue || 0) > 0 || (r.bookedRevenue || 0) > 0 || (r.pipelineCount || 0) > 0);
        }
        if (qStripped) {
            rows = rows.filter(r => {
                const name = (r.studentName || '').replace(/[\s　]+/g, '').toLowerCase();
                return name.includes(qStripped);
            });
        }
        return rows
            .sort((a, b) => (b.bookedRevenue || 0) - (a.bookedRevenue || 0))
            .map(r => {
                const fmtDate = (d) => {
                    if (!d) return '―';
                    const p = String(d).split('-');
                    return `${p[0]}/${parseInt(p[1])}/${parseInt(p[2])}`;
                };
                return {
                    studentId: r.studentId,
                    studentName: r.studentName || '―',
                    caName: r.caName || '―',
                    gradYear: r.gradYear || '―',
                    firstReferralDisplay:  fmtDate(r.firstReferralDate),
                    firstInterviewDisplay: fmtDate(r.firstInterviewDate),
                    acceptDateDisplay:     fmtDate(r.acceptDate),
                    realRevenueDisplay:    r.realRevenue > 0 ? '¥' + Number(Math.round(r.realRevenue)).toLocaleString() : '―',
                    bookedRevenueDisplay:  r.bookedRevenue > 0 ? '¥' + Number(Math.round(r.bookedRevenue)).toLocaleString() : '―',
                    leadTimeDisplay:       r.leadTimeDays != null ? r.leadTimeDays + '日' : '―',
                    latestStatusLabel:     (r.latestStatus || '―').replace(/^\d+\./, ''),
                    latestStatusClass:     this._calcStatusClass(r.latestStatus || ''),
                    pipelineCount:         r.pipelineCount || 0,
                    acceptedCompanies:     r.acceptedCompanies || '―'
                };
            });
    }

    // 月別コホートサマリー
    // basis='referral': 紹介月キー（firstReferralDate）— 集客効率視点
    // basis='accept'  : 承諾月キー（acceptDate, Field12優先）— 売上計上視点
    get monthlyCohortSummary() {
        if (!this._studentCohortRows.length) return [];
        const fy = parseInt(this.selectedYear, 10);
        if (isNaN(fy)) return [];
        // FY範囲: fy/6 〜 (fy+1)/5
        const inFY = (yr, mo) => (yr === fy && mo >= 6) || (yr === fy + 1 && mo <= 5);
        // FY内の月順インデックス（6→0, 7→1, ..., 12→6, 1→7, ..., 5→11）
        // 旧バグ: 2025/12と2026/1がいずれもord=6で衝突していた
        const fyMonthOrder = (yr, mo) => {
            if (yr === fy) return mo - 6;            // 6→0 .. 12→6
            if (yr === fy + 1) return 6 + mo;        // 1→7 .. 5→11
            return -1;
        };

        const inProgressPattern = /^(002|003|005|008|009|012|013|016|017|020|021|024)\./;
        const useAcceptBasis = this._cohortBasis === 'accept';

        const map = new Map();
        for (const r of this._studentCohortRows) {
            // 集計基準日を決定
            const baseDateStr = useAcceptBasis ? r.acceptDate : r.firstReferralDate;
            if (!baseDateStr) continue;
            const parts = String(baseDateStr).split('-');
            const yr = parseInt(parts[0], 10);
            const mo = parseInt(parts[1], 10);
            if (!inFY(yr, mo)) continue;
            const key = `${yr}/${mo}`;
            if (!map.has(key)) {
                map.set(key, {
                    key, ord: fyMonthOrder(yr, mo),
                    students: 0, interviewed: 0, totalPipes: 0,
                    accepted: 0, declined: 0, inProgress: 0,
                    totalReal: 0, totalBooked: 0,
                    prices: [], leadTimes: []
                });
            }
            const g = map.get(key);
            g.students++;
            if (r.firstInterviewDate) g.interviewed++;
            g.totalPipes += (r.pipelineCount || 0);
            const realIsZero = (r.realRevenue || 0) === 0;
            const bookedPositive = (r.bookedRevenue || 0) > 0;
            if (bookedPositive) {
                g.accepted++;
                g.totalBooked += r.bookedRevenue;
                g.prices.push(r.bookedRevenue);
                if (realIsZero) g.declined++;
            }
            if ((r.realRevenue || 0) > 0) g.totalReal += r.realRevenue;
            if (r.leadTimeDays != null && r.leadTimeDays >= 0) g.leadTimes.push(r.leadTimeDays);
            if (!bookedPositive && r.latestStatus && inProgressPattern.test(r.latestStatus)) {
                g.inProgress++;
            }
        }
        return [...map.values()]
            .sort((a, b) => a.ord - b.ord)
            .map(g => ({
                key: g.key,
                students: g.students,
                interviewed: g.interviewed,
                interviewRate: g.students > 0 ? (g.interviewed / g.students * 100).toFixed(1) + '%' : '―',
                totalPipes: g.totalPipes,
                accepted: g.accepted,
                acceptRate: g.students > 0 ? (g.accepted / g.students * 100).toFixed(1) + '%' : '―',
                declineRate: g.accepted > 0 ? (g.declined / g.accepted * 100).toFixed(1) + '%' : '―',
                avgLT: g.leadTimes.length > 0 ? Math.round(g.leadTimes.reduce((a, b) => a + b, 0) / g.leadTimes.length) + '日' : '―',
                avgPriceDisplay: g.prices.length > 0
                    ? '¥' + Number(Math.round(g.prices.reduce((a, b) => a + b, 0) / g.prices.length)).toLocaleString()
                    : '―',
                totalRealDisplay: g.totalReal > 0 ? '¥' + Number(Math.round(g.totalReal)).toLocaleString() : '―',
                totalBookedDisplay: g.totalBooked > 0 ? '¥' + Number(Math.round(g.totalBooked)).toLocaleString() : '―',
                inProgress: g.inProgress
            }));
    }
    get hasMonthlyCohort() { return this.monthlyCohortSummary.length > 0; }

    // basis切替UI用
    get cohortBasisLabel() { return this._cohortBasis === 'accept' ? '承諾月' : '紹介月'; }
    get cohortBasisIsReferral() { return this._cohortBasis === 'referral'; }
    get cohortBasisIsAccept()   { return this._cohortBasis === 'accept'; }
    get referralBtnClass() { return 'gkd-toggle-btn' + (this.cohortBasisIsReferral ? ' gkd-toggle-btn--active' : ''); }
    get acceptBtnClass()   { return 'gkd-toggle-btn' + (this.cohortBasisIsAccept   ? ' gkd-toggle-btn--active' : ''); }
    handleCohortBasisReferral() { this._cohortBasis = 'referral'; }
    handleCohortBasisAccept()   { this._cohortBasis = 'accept'; }

    // 全期間 平均承諾単価（KPIカード用）
    get cohortOverallAvgAcceptPrice() {
        const accepted = this._studentCohortRows.filter(r => (r.bookedRevenue || 0) > 0);
        if (!accepted.length) return null;
        const total = accepted.reduce((s, r) => s + r.bookedRevenue, 0);
        return Math.round(total / accepted.length);
    }
    get cohortAvgAcceptPriceDisplay() {
        const v = this.cohortOverallAvgAcceptPrice;
        return v != null ? '¥' + Number(v).toLocaleString() : '―';
    }

    get cohortKpi() {
        if (!this._studentCohortRows.length) return null;
        const total = this._studentCohortRows.length;
        // 承諾済 = 025+027（一度でも承諾に到達）= bookedRevenue>0 で判定
        const accepted = this._studentCohortRows.filter(r => (r.bookedRevenue || 0) > 0).length;
        const totalReal = this._studentCohortRows.reduce((s, r) => s + (r.realRevenue || 0), 0);
        const totalBooked = this._studentCohortRows.reduce((s, r) => s + (r.bookedRevenue || 0), 0);
        const leadTimes = this._studentCohortRows.filter(r => r.leadTimeDays != null).map(r => r.leadTimeDays);
        const avgLead = leadTimes.length ? Math.round(leadTimes.reduce((a, b) => a + b, 0) / leadTimes.length) : null;
        return {
            total,
            accepted,
            acceptRate: total > 0 ? (accepted / total * 100).toFixed(1) + '%' : '―',
            realDisplay: '¥' + Number(Math.round(totalReal)).toLocaleString(),
            bookedDisplay: '¥' + Number(Math.round(totalBooked)).toLocaleString(),
            avgLeadDisplay: avgLead != null ? avgLead + '日' : '―'
        };
    }

    handleExportCohortCSV() {
        if (!this.studentCohortRows.length) return;
        const headers = ['学生名','担当CA','卒年','直近ステータス','紹介日','初回面談日','承諾日','リードタイム','案件数','実売上','計上売上','承諾企業'];
        const lines = [headers.join(',')];
        for (const r of this.studentCohortRows) {
            const stripYen = (s) => String(s).replace(/[¥,]/g, '');
            lines.push([
                r.studentName, r.caName, r.gradYear, r.latestStatusLabel,
                r.firstReferralDisplay, r.firstInterviewDisplay, r.acceptDateDisplay,
                r.leadTimeDisplay, r.pipelineCount,
                stripYen(r.realRevenueDisplay), stripYen(r.bookedRevenueDisplay),
                r.acceptedCompanies
            ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','));
        }
        this._downloadCsv(lines.join('\n'), `学生別売上_${this.selectedYear || 'all'}.csv`);
    }

    // CSVダウンロード共通ヘルパー（LWC + LightningWebSecurity 対応）
    // データURI方式: BlobURLはLWSで失敗するケースがあるため非採用
    _downloadCsv(csvContent, filename) {
        try {
            const bom = '\uFEFF';
            const dataUri = 'data:text/csv;charset=utf-8,' + encodeURIComponent(bom + csvContent);
            const a = document.createElement('a');
            a.setAttribute('href', dataUri);
            a.setAttribute('download', filename);
            a.setAttribute('target', '_self');
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                try { document.body.removeChild(a); } catch (e) { /* noop */ }
            }, 500);
            this.dispatchEvent(new ShowToastEvent({
                title: 'CSV出力',
                message: filename,
                variant: 'success'
            }));
        } catch (err) {
            try {
                const bom2 = '\uFEFF';
                const dataUri2 = 'data:text/csv;charset=utf-8,' + encodeURIComponent(bom2 + csvContent);
                window.open(dataUri2, '_blank');
            } catch (e2) {
                this.dispatchEvent(new ShowToastEvent({
                    title: 'CSV出力失敗',
                    message: (err && err.message) || 'ダウンロードできません',
                    variant: 'error'
                }));
            }
        }
    }
    async handleTeamYomiStatusChange(e) {
        const pipelineId = e.target.dataset.id;
        const newStatus = e.target.value;
        this._teamYomiRows = this._teamYomiRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, status: newStatus } : r
        );
        try {
            await updatePipelineStatusAndAccuracy({ pipelineId, newStatus, newAccuracy: null });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message || String(err), variant: 'error' }));
        }
    }
    async handleTeamYomiAccuracyChange(e) {
        const pipelineId = e.target.dataset.id;
        const newAccuracy = e.target.value || null;
        this._teamYomiRows = this._teamYomiRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, accuracy: newAccuracy } : r
        );
        try {
            await updatePipelineStatusAndAccuracy({ pipelineId, newStatus: null, newAccuracy });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message || String(err), variant: 'error' }));
        }
    }
    handleCAChange(e) {
        this.selectedCA = e.detail.value;
        this.loadByname();
    }
    handleYomiMonthChange(e) {
        this.selectedYomiMonth = e.detail.value;
        this.loadByname();
    }
    handlePhaseChange(e) {
        this.selectedPhase = e.detail.value;
    }
    handleShowInactiveToggle(e) {
        this._showInactive = e.target.checked;
        this._bynameRows = [];
        this.loadByname();
    }
    handleOnlyYomiFlagToggle(e) {
        // クライアント側フィルタなので再ロード不要（bynameGrouped getter で動的に絞り込み）
        this._onlyYomiFlag = e.target.checked;
    }
    handleStudentNameSearch(e) {
        // 学生名 部分一致絞り込み（クライアントサイド・スペース全除去で柔軟に）
        this._studentNameQuery = (e.target.value || '').replace(/[\s　]+/g, '');
    }
    handleCompanySearch(e) {
        this._companyQuery = (e.target.value || '').replace(/[\s　]+/g, '');
    }
    handleAccuracyFilterChange(e) {
        this._selectedAccuracyFilter = e.target.value || '';
    }
    get accuracyFilterOptions() {
        return [{ label: '全精度', value: '' }, ...ACCURACY_OPTIONS];
    }
    // --- Tab6 ソート ---
    get sortFieldOptions() {
        return [
            { label: '面談日', value: 'meetingDate' },
            { label: '加重ヨミ', value: 'totalYomi' },
            { label: '承諾率', value: 'acceptRate' },
            { label: '実売上', value: 'realRevenue' },
            { label: '学生名', value: 'studentName' },
        ];
    }
    get sortDirOptions() {
        return [
            { label: '降順 (新しい/大きい順)', value: 'desc' },
            { label: '昇順 (古い/小さい順)', value: 'asc' },
        ];
    }
    handleSortFieldChange(e) { this._sortField = e.detail.value; }
    handleSortDirChange(e) { this._sortDir = e.detail.value; }
    async handleBynameStatusChange(e) {
        const pipelineId = e.target.dataset.id;
        const newStatus = e.target.value;
        this._bynameRows = this._bynameRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, status: newStatus } : r
        );
        try {
            await updatePipelineFields({ pipelineId, newStatus, newAccuracy: null, yomiMonthStr: null, newUnitPrice: null });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }
    async handleBynameAccuracyChange(e) {
        const pipelineId = e.target.dataset.id;
        const newAccuracy = e.target.value || null;
        this._bynameRows = this._bynameRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, accuracy: newAccuracy } : r
        );
        try {
            await updatePipelineFields({ pipelineId, newStatus: null, newAccuracy, yomiMonthStr: null, newUnitPrice: null });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }
    async handleBynameYomiMonthChange(e) {
        const pipelineId = e.target.dataset.id;
        const yomiMonthStr = e.target.value || '';
        this._bynameRows = this._bynameRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, yomiMonth: yomiMonthStr || null } : r
        );
        try {
            await updatePipelineFields({ pipelineId, newStatus: null, newAccuracy: null, yomiMonthStr, newUnitPrice: null });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    // ===== Tab8: 企業別進捗管理 =====
    get companyTabQueryShort() { return this._companyTabQuery.length < 3; }

    async loadCompanyNames() {
        try {
            this._companyNames = await getCompanyNamesWithActivePipelines();
        } catch (e) { /* silent */ }
    }

    get filteredCompanyOptions() {
        const q = (this._companyTabQuery || '').toLowerCase();
        const list = q
            ? this._companyNames.filter(n => n.toLowerCase().includes(q))
            : this._companyNames;
        return list.slice(0, 50).map(n => ({
            value: n,
            label: n,
            itemClass: 'gkd-ca-item' + (this._companyTabQuery === n ? ' gkd-ca-item-selected' : '')
        }));
    }

    handleCompanyTabQueryInput(e) {
        this._companyTabQuery = (e.target.value || '').replace(/[\s　]+/g, '');
        this._companyDropdownOpen = true;
        if (this._companyTabQuery.length >= 3) {
            this.loadCompanyTab();
        } else {
            this._companyTabRows = [];
        }
    }

    handleCompanyTabSearchFocus() {
        this._companyDropdownOpen = true;
        if (this._companyNames.length === 0) this.loadCompanyNames();
    }

    handleCompanyTabSearchBlur() {
        setTimeout(() => { this._companyDropdownOpen = false; }, 200);
    }

    handleCompanyOptionClick(e) {
        const val = e.currentTarget.dataset.value;
        this._companyTabQuery = val;
        this._companyDropdownOpen = false;
        this.loadCompanyTab();
    }

    async loadCompanyTab() {
        this._isCompanyTabLoading = true;
        try {
            this._companyTabRows = await getCompanyPipelines({
                companyQuery: this._companyTabQuery,
                caName: this._companyTabCA || null,       // Tab8専用CAフィルタ
                gradYear: this._companyTabGradYear || null,  // Tab8専用卒年フィルタ
                fiscalYear: this.selectedYear || null
            });
        } catch (e) {
            this.showError(e);
        } finally {
            this._isCompanyTabLoading = false;
        }
    }
    handleCompanyTabCAChange(e) {
        this._companyTabCA = e.detail.value || '';
        if (this._companyTabQuery.length >= 3) this.loadCompanyTab();
    }
    handleCompanyTabGradYearChange(e) {
        this._companyTabGradYear = e.detail.value || '';
        if (this._companyTabQuery.length >= 3) this.loadCompanyTab();
    }
    handleCompanyTabPhaseChange(e) {
        // client-side フィルタなので reload 不要
        this._companyTabPhase = e.detail.value || '';
    }

    get companyTabPhaseOptions() {
        return [
            { label: '全て',         value: '' },
            { label: '説明会以降',   value: 'session' },
            { label: '面接以降',     value: 'interview' },
            { label: '最終以降',     value: 'final' },
            { label: '内定以降',     value: 'offer' },
            { label: '承諾済のみ',   value: 'accepted' },
            { label: '辞退',         value: 'declined' }
        ];
    }

    _matchPhase(status) {
        const ph = this._companyTabPhase;
        if (!ph) return true;
        const s = status || '';
        switch (ph) {
            case 'session':   return s >= '003.';
            case 'interview': return s >= '008.' && s < '028.';
            case 'final':     return s >= '020.' && s < '028.';
            case 'offer':     return s >= '024.' && s < '028.';
            case 'accepted':  return s === '025.内定承諾';
            case 'declined':  return s === '026.内定後辞退' || s === '027.内定承諾後辞退';
            default: return true;
        }
    }

    async handleCompanyTabStatusChange(e) {
        const pipelineId = e.target.dataset.id;
        const newStatus = e.target.value;
        this._companyTabRows = this._companyTabRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, status: newStatus } : r
        );
        try {
            await updatePipelineFields({ pipelineId, newStatus, newAccuracy: null, yomiMonthStr: null, newUnitPrice: null });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    async handleCompanyTabAccuracyChange(e) {
        const pipelineId = e.target.dataset.id;
        const newAccuracy = e.target.value || null;
        this._companyTabRows = this._companyTabRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, accuracy: newAccuracy } : r
        );
        try {
            await updatePipelineFields({ pipelineId, newStatus: null, newAccuracy, yomiMonthStr: null, newUnitPrice: null });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    async handleCompanyTabYomiMonthChange(e) {
        const pipelineId = e.target.dataset.id;
        const yomiMonthStr = e.target.value || '';
        this._companyTabRows = this._companyTabRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, yomiMonth: yomiMonthStr || null } : r
        );
        try {
            await updatePipelineFields({ pipelineId, newStatus: null, newAccuracy: null, yomiMonthStr, newUnitPrice: null });
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    // プラットフォーム求人（CIRCUS等）専用: 個別企業名を保存
    async handleCompanyTabIndividualNameBlur(e) {
        const pipelineId = e.target.dataset.id;
        const newName = (e.target.value || '').trim();
        const current = this._companyTabRows.find(r => r.pipelineId === pipelineId);
        const prev = (current?.individualCompanyName || '').trim();
        if (newName === prev) return;
        this._companyTabRows = this._companyTabRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, individualCompanyName: newName || null } : r
        );
        try {
            await updatePipelineFieldsV2({
                pipelineId, newStatus: null, newAccuracy: null, yomiMonthStr: null,
                newUnitPrice: null, newIndividualCompanyName: newName
            });
            this.dispatchEvent(new ShowToastEvent({ title: '保存しました', variant: 'success' }));
            // 企業名変更でグループが変わるため再読込
            this.loadCompanyTab();
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    // プラットフォーム求人（CIRCUS等）専用: 単価を保存（円・空欄でクリア）
    async handleCompanyTabUnitPriceBlur(e) {
        const pipelineId = e.target.dataset.id;
        const raw = (e.target.value || '').trim();
        const newUnitPrice = raw === '' ? null : Number(raw);
        if (raw !== '' && isNaN(newUnitPrice)) {
            this.dispatchEvent(new ShowToastEvent({ title: '入力エラー', message: '数値で入力してください', variant: 'error' }));
            return;
        }
        this._companyTabRows = this._companyTabRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, unitPrice: newUnitPrice } : r
        );
        try {
            await updatePipelineFieldsV2({
                pipelineId, newStatus: null, newAccuracy: null, yomiMonthStr: null,
                newUnitPrice, newIndividualCompanyName: null
            });
            this.dispatchEvent(new ShowToastEvent({ title: '保存しました', variant: 'success' }));
            this.loadCompanyTab();
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    _processCompanyTabRow(r) {
        const st = r.status || '';
        const hasPrice = r.unitPrice != null;
        return {
            ...r,
            statusClass: this._calcStatusClass(st),
            caName: r.caName || '―',
            yomiDisplay: hasPrice ? '¥' + Number(Math.round(r.weightedYomiAmt || 0)).toLocaleString() : '―',
            unitPriceDisplay: r.unitPrice != null ? Number(r.unitPrice) : null,
            individualCompanyNameDisplay: r.individualCompanyName || '',
            statusOptionsWithSelected: STATUS_OPTIONS.map(o => ({ ...o, selected: o.value === st })),
            accuracyOptionsWithSelected: [{ label: '―', value: '', selected: !r.accuracy },
                ...ACCURACY_OPTIONS.map(o => ({ ...o, selected: o.value === r.accuracy }))],
            yomiMonthOptionsWithSelected: this._buildYomiMonthOptions(r.yomiMonth ? String(r.yomiMonth).substring(0, 7) : '')
        };
    }

    get hasCompanyTabData() { return this._companyTabRows.length > 0; }

    get companyTabKpi() {
        const rows = this._companyTabRows;
        if (rows.length === 0) return null;
        const interviewActive = new Set([
            '008.一次面接参加予定','009.一次面接通過',
            '012.二次面接参加予定','013.二次面接通過',
            '016.三次面接参加予定','017.三次面接通過',
            '020.最終面接参加予定','021.最終面接通過'
        ]);
        const sessionAfter = new Set([
            '002.説明会参加予定','003.説明会参加済み','005.書類選考・適性検査',
            '008.一次面接参加予定','009.一次面接通過',
            '012.二次面接参加予定','013.二次面接通過',
            '016.三次面接参加予定','017.三次面接通過',
            '020.最終面接参加予定','021.最終面接通過',
            '024.内定','025.内定承諾'
        ]);
        const referrals = rows.length;
        const sessionCount = rows.filter(r => sessionAfter.has(r.status)).length;
        const interviewCount = rows.filter(r => interviewActive.has(r.status)).length;
        const offerCount = rows.filter(r => r.status === '024.内定').length;
        const acceptedCount = rows.filter(r => r.status === '025.内定承諾').length;
        const realRevenue = rows
            .filter(r => r.status === '025.内定承諾')
            .reduce((s, r) => s + (r.unitPrice || 0), 0);
        const weightedYomi = rows.reduce((s, r) => s + (r.weightedYomiAmt || 0), 0);
        const totalOffer = offerCount + acceptedCount;
        return {
            companyCount: new Set(rows.map(r => r.companyName || '（求人票未設定）')).size,
            studentCount: new Set(rows.map(r => r.studentId || r.pipelineId)).size,
            referrals,
            sessionCount,
            interviewCount,
            offerCount,
            acceptedCount,
            sessionToOfferRate: sessionCount > 0 ? (totalOffer / sessionCount * 100).toFixed(1) + '%' : '―',
            offerToAcceptRate: totalOffer > 0 ? (acceptedCount / totalOffer * 100).toFixed(1) + '%' : '―',
            referralToAcceptRate: referrals > 0 ? (acceptedCount / referrals * 100).toFixed(1) + '%' : '―',
            realRevenueDisplay: '¥' + Number(Math.round(realRevenue)).toLocaleString(),
            weightedYomiDisplay: '¥' + Number(Math.round(weightedYomi)).toLocaleString()
        };
    }

    get companyTabGrouped() {
        const map = new Map();
        for (const r of this._companyTabRows) {
            if (!this._matchPhase(r.status)) continue;
            const key = r.companyName || '（求人票未設定）';
            if (!map.has(key)) {
                map.set(key, { key, companyName: key, rows: [], acceptedCount: 0, hasPlatformJob: false });
            }
            const grp = map.get(key);
            grp.rows.push(this._processCompanyTabRow(r));
            if (r.status === '025.内定承諾') grp.acceptedCount++;
            if (r.isPlatformJob) grp.hasPlatformJob = true;
        }
        return [...map.values()]
            .sort((a, b) => a.companyName.localeCompare(b.companyName))
            .map(g => ({ ...g, studentCount: g.rows.length }));
    }

    handleCASearchInput(e) {
        this._caInputValue = e.target.value;
        this._caSearchText = e.target.value;
        this._caDropdownOpen = true;
    }
    handleCASearchFocus() {
        this._caSearchText = '';           // フォーカス時は全件表示
        this._caInputValue = '';           // 入力欄をクリアして検索しやすく
        this._caDropdownOpen = true;
    }
    handleCAOptionClick(e) {
        const val = e.currentTarget.dataset.value;
        const label = e.currentTarget.dataset.label;
        this.selectedCA = val;
        this._caInputValue = label;
        this._caSearchText = '';
        this._caDropdownOpen = false;
        this._studentCohortRows = [];   // 常にクリア
        if (this.activeTab === 6) this.loadByname();
        if (this.activeTab === 9) this.loadStudentCohort();
    }
    handleCASearchBlur() {
        setTimeout(() => {
            this._caDropdownOpen = false;
            // 何も選択せず blur した場合、現在の選択値に戻す
            this._caInputValue = this.selectedCA || '全CA';
            this._caSearchText = '';
        }, 200);
    }
    @track _clSource = 'byname'; // 'byname'=Tab6 / 'team'=Tab7

    handleOpenDetail(e) {
        const id = e.currentTarget.dataset.id;
        this._detailPipelineId = id;
        this._clSource = 'byname';
        const row = this._bynameRows.find(r => r.pipelineId === id);
        if (row) {
            this._checklistState = {
                q1: !!row.q1, q2: !!row.q2, q3: !!row.q3, q4: !!row.q4, q5: !!row.q5,
                q6: !!row.q6, q7: !!row.q7, q8: !!row.q8, q9: !!row.q9, q10: !!row.q10
            };
        } else {
            this._checklistState = { q1:false,q2:false,q3:false,q4:false,q5:false,q6:false,q7:false,q8:false,q9:false,q10:false };
        }
        this._showDetailModal = true;
    }
    handleOpenChecklistFromTeam(e) {
        const id = e.currentTarget.dataset.id;
        this._detailPipelineId = id;
        this._clSource = 'team';
        // Team行からチェック状態を取得（q1〜q10は未保持のため全falseスタート）
        const row = this._teamYomiRows.find(r => r.pipelineId === id);
        this._checklistState = row
            ? { q1: !!row.q1, q2: !!row.q2, q3: !!row.q3, q4: !!row.q4, q5: !!row.q5,
                q6: !!row.q6, q7: !!row.q7, q8: !!row.q8, q9: !!row.q9, q10: !!row.q10 }
            : { q1:false,q2:false,q3:false,q4:false,q5:false,q6:false,q7:false,q8:false,q9:false,q10:false };
        this._showDetailModal = true;
    }
    handleCloseModal() {
        this._showDetailModal = false;
        this._detailPipelineId = null;
    }
    async handleModalSaved() {
        this._showDetailModal = false;
        this._detailPipelineId = null;
        this.dispatchEvent(new ShowToastEvent({ title: '保存しました', variant: 'success' }));
        await this.loadByname();
    }
    handleChecklistToggle(e) {
        const key = e.currentTarget.dataset.key;
        this._checklistState = { ...this._checklistState, [key]: !this._checklistState[key] };
    }
    async handleSaveChecklist() {
        const id = this._detailPipelineId;
        const s = this._checklistState;
        const newCount = Object.values(s).filter(Boolean).length;
        try {
            await saveAcceptChecklist({ pipelineId: id, q1: s.q1, q2: s.q2, q3: s.q3, q4: s.q4, q5: s.q5, q6: s.q6, q7: s.q7, q8: s.q8, q9: s.q9, q10: s.q10 });
            if (this._clSource === 'team') {
                this._teamYomiRows = this._teamYomiRows.map(r =>
                    r.pipelineId === id ? { ...r, ...s, acceptCount: newCount } : r
                );
            } else {
                this._bynameRows = this._bynameRows.map(r =>
                    r.pipelineId === id ? { ...r, ...s, acceptCount: newCount } : r
                );
            }
            this.dispatchEvent(new ShowToastEvent({ title: 'チェックリストを保存しました', variant: 'success' }));
        } catch(err) {
            this.dispatchEvent(new ShowToastEvent({ title: '保存エラー', message: err.body?.message, variant: 'error' }));
        }
    }
    get checklistItems() {
        const labels = [
            '志望度ヒアリング済み', '年収・処遇への納得確認', '就活軸との合致確認',
            '懸念点・不安の解消済み', '他社オファー状況の把握', '内定後フォロー面談実施',
            '家族・周囲への相談済み', '入社後キャリアパスの理解', '承諾後辞退リスクの確認',
            '最終入社意欲の再確認'
        ];
        const s = this._checklistState;
        const keys = ['q1','q2','q3','q4','q5','q6','q7','q8','q9','q10'];
        return keys.map((k, i) => ({
            key: k,
            label: `Q${i+1}. ${labels[i]}`,
            itemClass: 'gkd-cl-item' + (s[k] ? ' gkd-cl-item--checked' : ''),
            checkClass: 'gkd-cl-check' + (s[k] ? ' gkd-cl-check--on' : '')
        }));
    }
    get checklistCheckedCount() {
        return Object.values(this._checklistState).filter(Boolean).length;
    }
    get checklistRecommendedGrade() {
        const n = this.checklistCheckedCount;
        if (n >= 9) return 'S';
        if (n >= 7) return 'A';
        if (n >= 5) return 'B';
        if (n >= 3) return 'C';
        return 'D';
    }
    get checklistGradeClass() {
        const g = this.checklistRecommendedGrade;
        return 'gkd-cl-grade gkd-cl-grade--' + g.toLowerCase();
    }
    get checklistProgressStyle() {
        const pct = this.checklistCheckedCount * 10;
        return `width:${pct}%`;
    }
    get detailStudentName() {
        if (!this._detailPipelineId) return '';
        const row = this._bynameRows.find(r => r.pipelineId === this._detailPipelineId);
        return row ? row.studentName : '';
    }
    get detailCompanyName() {
        if (!this._detailPipelineId) return '';
        const row = this._bynameRows.find(r => r.pipelineId === this._detailPipelineId);
        return row ? (row.companyName || '') : '';
    }

    // ===== Tab7: チームヨミ管理 =====
    get isTab7() { return this.activeTab === 7; }

    _calcStatusClass(st) {
        let cls = 'gkd-status-badge';
        if (st === '025.内定承諾') cls += ' gkd-status-accepted';
        else if (st === '024.内定') cls += ' gkd-status-offer';
        else if (st === '020.最終面接参加予定' || st === '021.最終面接通過') cls += ' gkd-status-final';
        else if (/0(08|09|12|13|16|17)\./.test(st)) cls += ' gkd-status-interview';
        return cls;
    }
    get tab7Class() { return `gkd-tab${this.activeTab === 7 ? ' gkd-tab-active' : ''}`; }

    get teamYomiMonthOptions() {
        // 表示順: 今月 → 来月 → 再来月 → ... → 11ヶ月先 → 先月 → 先々月 → 3ヶ月前
        // （直近・未来のヨミ予定をすぐ確認できるよう未来寄りを上に配置）
        const opts = [];
        const now = new Date();
        const fmt = (d) => ({
            val: `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`,
            label: `${d.getFullYear()}/${d.getMonth()+1}月`
        });
        // 今月から12ヶ月先
        for (let i = 0; i <= 11; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
            const f = fmt(d);
            opts.push({ label: i === 0 ? `${f.label}（今月）` : f.label, value: f.val });
        }
        // 過去3ヶ月（参照用）
        for (let i = -1; i >= -3; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
            const f = fmt(d);
            opts.push({ label: f.label, value: f.val });
        }
        return opts;
    }
    get teamYomiCAOptions() {
        const cas = [...new Set(this._teamYomiRows.map(r => r.caName).filter(Boolean))].sort();
        return [{ label: '全CA', value: '' }, ...cas.map(c => ({ label: c, value: c }))];
    }

    get teamYomiFiltered() {
        let rows = this._teamYomiRows;
        if (this._selectedTeamYomiCA) rows = rows.filter(r => r.caName === this._selectedTeamYomiCA);
        // 1学生1社: yomiFlag=true を優先し、それ以外は加重ヨミ降順で先頭1件を残す
        const sorted = [...rows].sort((a, b) => {
            if (a.yomiFlag !== b.yomiFlag) return a.yomiFlag ? -1 : 1;
            return (b.weightedYomi || 0) - (a.weightedYomi || 0);
        });
        const seen = new Set();
        return sorted.filter(r => {
            if (seen.has(r.studentId)) return false;
            seen.add(r.studentId);
            return true;
        });
    }

    get teamYomiGrouped() {
        const map = new Map();
        for (const r of this.teamYomiFiltered) {
            const key = r.yomiMonth ? String(r.yomiMonth).substring(0,7) : 'なし';
            if (!map.has(key)) map.set(key, { key, label: key === 'なし' ? 'ヨミ月未設定' : this._formatYomiMonthLabel(key), rows: [], totalYomi: 0, acceptedCount: 0 });
            const grp = map.get(key);
            const processed = this._processTeamRow(r);
            grp.rows.push(processed);
            grp.totalYomi += r.weightedYomi || 0;
            if (r.status === '025.内定承諾') grp.acceptedCount++;
        }
        return [...map.values()].map(g => ({
            ...g,
            totalYomiDisplay: '¥' + Number(Math.round(g.totalYomi)).toLocaleString(),
            count: g.rows.length
        })).sort((a, b) => a.key.localeCompare(b.key));
    }

    get teamYomiKpi() {
        const rows = this.teamYomiFiltered;
        const totalYomi = rows.reduce((s, r) => s + (r.weightedYomi || 0), 0);
        const accepted  = rows.filter(r => r.status === '025.内定承諾').length;
        const avgRate   = rows.length > 0 ? rows.reduce((s, r) => s + (r.acceptRate || 0), 0) / rows.length : 0;
        const realRev   = rows.filter(r => r.status === '025.内定承諾').reduce((s, r) => s + (r.unitPrice || 0), 0);
        // 計上売上 = 内定承諾 + 内定承諾後辞退 の単価合計
        const bookedRev = rows.filter(r => r.status === '025.内定承諾' || r.status === '027.内定承諾後辞退')
                              .reduce((s, r) => s + (r.unitPrice || 0), 0);
        // ★ヨミ（YomiFlag=true）集計（単価ベース）
        const yomiFlagRows = rows.filter(r => r.yomiFlag === true);
        const yomiFlagUnitTotal = yomiFlagRows.reduce((s, r) => s + (r.unitPrice || 0), 0);
        return {
            count: rows.length,
            accepted,
            totalYomiDisplay: '¥' + Number(Math.round(totalYomi)).toLocaleString(),
            realRevDisplay:   '¥' + Number(Math.round(realRev)).toLocaleString(),
            bookedRevDisplay: '¥' + Number(Math.round(bookedRev)).toLocaleString(),
            avgRateDisplay: avgRate.toFixed(1) + '%',
            yomiFlagCount: yomiFlagRows.length,
            yomiFlagUnitDisplay: '¥' + Number(Math.round(yomiFlagUnitTotal)).toLocaleString()
        };
    }

    get quarterlyYomiGroups() {
        const qMap = {};
        for (const r of this.teamYomiFiltered) {
            if (!r.yomiMonth) continue;
            const parts = String(r.yomiMonth).split('-');
            const yr = parseInt(parts[0]); const mo = parseInt(parts[1]);
            const fy = mo >= 6 ? yr : yr - 1;
            const q  = (mo >= 6 && mo <= 8) ? 'Q1'
                     : (mo >= 9 && mo <= 11) ? 'Q2'
                     : (mo === 12 || mo <= 2) ? 'Q3'
                     : 'Q4';
            const key = `${fy}年度 ${q}`;
            if (!qMap[key]) qMap[key] = { key, label: key, yomi: 0, accepted: 0, count: 0 };
            qMap[key].yomi += r.weightedYomi || 0;
            qMap[key].count++;
            if (r.status === '025.内定承諾') qMap[key].accepted++;
        }
        return Object.values(qMap)
            .sort((a, b) => a.key.localeCompare(b.key))
            .map(q => ({ ...q, yomiDisplay: '¥' + Number(Math.round(q.yomi)).toLocaleString() }));
    }

    _formatYomiMonthLabel(key) {
        if (!key || key === 'なし') return 'ヨミ月未設定';
        const [yr, mo] = key.split('-');
        return `${yr}年${parseInt(mo)}月`;
    }

    _processTeamRow(r) {
        const st = r.status || '';
        const statusClass = this._calcStatusClass(st);

        let naDateDisplay = '';
        if (r.naDate) {
            const p = String(r.naDate).split('-');
            naDateDisplay = `${parseInt(p[1])}/${parseInt(p[2])}`;
        }

        const checkCount = r.acceptCount != null ? Number(r.acceptCount) : 0;
        const rate = Math.min(Math.round(checkCount / 10 * 100), 100);
        const rateClass = rate >= 80 ? 'gkd-ty-rate gkd-ty-rate--high' : rate >= 40 ? 'gkd-ty-rate gkd-ty-rate--mid' : 'gkd-ty-rate gkd-ty-rate--low';
        const checkGrade = checkCount >= 9 ? 'S' : checkCount >= 7 ? 'A' : checkCount >= 5 ? 'B' : checkCount >= 3 ? 'C' : 'D';
        const checkGradeClass = 'gkd-cl-grade gkd-cl-grade--' + checkGrade.toLowerCase();
        const accuracyClass = 'gkd-accuracy' + (r.accuracy === 'S' ? ' gkd-acc-s' : r.accuracy === 'A' ? ' gkd-acc-a' : r.accuracy === 'B' ? ' gkd-acc-b' : r.accuracy === 'C' ? ' gkd-acc-c' : '');
        const ed = this._teamYomiEditMap[r.pipelineId] || {};

        const currentYM = r.yomiMonth ? String(r.yomiMonth).substring(0, 7) : '';
        return {
            ...r,
            statusLabel: st.replace(/^\d+\./, ''),
            statusClass,
            naDateDisplay,
            rateDisplay: rate.toFixed(0) + '%',
            rateClass,
            weightedYomiDisplay: r.weightedYomi > 0 ? '¥' + Number(Math.round(r.weightedYomi)).toLocaleString() : '―',
            yomiFlagClass: r.yomiFlag ? 'gkd-yomi-flag gkd-yomi-flag--on' : 'gkd-yomi-flag',
            editingSituation: ed.situation !== undefined ? ed.situation : (r.situation || ''),
            editingNaDate:    ed.naDate    !== undefined ? ed.naDate    : (r.naDate ? String(r.naDate) : ''),
            editingNaDetail:  ed.naDetail  !== undefined ? ed.naDetail  : (r.naDetail || ''),
            editingOther:     ed.other     !== undefined ? ed.other     : (r.otherCompany || ''),
            checkCount, checkGrade, checkGradeClass,
            accuracyClass, accuracyLabel: r.accuracy || '―',
            statusOptionsWithSelected: STATUS_OPTIONS.map(o => ({ ...o, selected: o.value === st })),
            accuracyOptionsWithSelected: [{ label: '―', value: '', selected: !r.accuracy },
                ...ACCURACY_OPTIONS.map(o => ({ ...o, selected: o.value === r.accuracy }))],
            yomiMonthOptionsWithSelected: this._buildYomiMonthOptions(currentYM),
            rowClass: (r.status === '025.内定承諾' ? 'gkd-ty-row--accepted' : '') + (r.yomiFlag ? ' gkd-ty-row--yomi' : '')
        };
    }

    _buildYomiMonthOptions(currentYM) {
        const opts = [{ label: '―', value: '', selected: !currentYM }];
        const now = new Date();
        for (let i = -11; i <= 3; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
            const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            opts.push({ label: `${d.getFullYear()}/${d.getMonth() + 1}月`, value: val, selected: val === currentYM });
        }
        return opts;
    }

    async handleTeamYomiMonthRowChange(e) {
        const pipelineId = e.target.dataset.id;
        const yomiMonthStr = e.target.value; // "YYYY-MM" or ""
        this._teamYomiRows = this._teamYomiRows.map(r =>
            r.pipelineId === pipelineId ? { ...r, yomiMonth: yomiMonthStr || null } : r
        );
        try {
            await updatePipelineFields({ pipelineId, newStatus: null, newAccuracy: null, yomiMonthStr: yomiMonthStr, newUnitPrice: null });
            await this.loadTeamYomi();
        } catch (err) {
            this.dispatchEvent(new ShowToastEvent({ title: '更新エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    async loadTeamYomi() {
        this._isTeamYomiLoading = true;
        try {
            const recs = await getTeamYomiData({
                fiscalYear: this.selectedYear || null,
                caName: this._selectedTeamYomiCA || null,
                yomiMonth: this._effectiveYomiMonth(this._selectedTeamYomiMonth)
            });
            this._teamYomiRows = recs || [];
        } catch(e) {
            this.dispatchEvent(new ShowToastEvent({ title: 'データ取得エラー', message: e.body?.message, variant: 'error' }));
        } finally {
            this._isTeamYomiLoading = false;
        }
    }

    async loadConsultantMonthly() {
        this._isConsultantMonthlyLoading = true;
        try {
            this._consultantMonthlyData = await getConsultantMonthlyRevenue({ fiscalYear: this.selectedYear || null });
        } catch(e) {
            this.dispatchEvent(new ShowToastEvent({ title: 'データ取得エラー', message: e.body?.message, variant: 'error' }));
        } finally {
            this._isConsultantMonthlyLoading = false;
        }
    }

    get fyMonthLabels() {
        return [
            { key: '0', label: '6月' }, { key: '1', label: '7月' }, { key: '2', label: '8月' },
            { key: '3', label: '9月' }, { key: '4', label: '10月' }, { key: '5', label: '11月' },
            { key: '6', label: '12月' }, { key: '7', label: '1月' }, { key: '8', label: '2月' },
            { key: '9', label: '3月' }, { key: '10', label: '4月' }, { key: '11', label: '5月' },
        ];
    }

    get consultantMonthlyRows() {
        if (!this._consultantMonthlyData?.length) return [];
        const maxRev = Math.max(...this._consultantMonthlyData.map(r => r.totalRevenue || 0), 1);
        return [...this._consultantMonthlyData]
            .sort((a, b) => (b.totalRevenue || 0) - (a.totalRevenue || 0))
            .map(r => ({
                caName: r.caName,
                totalRevDisplay: '¥' + Number(Math.round(r.totalRevenue || 0)).toLocaleString(),
                totalAccepted: r.totalAccepted || 0,
                barWidth: Math.round(((r.totalRevenue || 0) / maxRev) * 100),
                barStyle: `width:${Math.round(((r.totalRevenue || 0) / maxRev) * 100)}%`,
                months: (r.monthlyRevenue || []).map((rev, i) => ({
                    key: String(i),
                    caName: r.caName,
                    monthIdx: String(i),
                    revDisplay: rev > 0 ? Math.round(rev / 10000) + '万' : '―',
                    cellClass: rev > 0 ? 'gkd-cm-cell gkd-cm-cell--hit gkd-cm-cell--clickable' : 'gkd-cm-cell',
                    clickable: rev > 0,
                })),
            }));
    }

    handleCmCellClick(e) {
        const ca = e.currentTarget.dataset.ca;
        const idx = parseInt(e.currentTarget.dataset.month, 10);
        this._cmDetailCa = ca;
        this._cmDetailMonthIdx = idx;
        this._showCmDetailModal = true;
    }
    handleCmDetailClose() {
        this._showCmDetailModal = false;
        this._cmDetailCa = null;
        this._cmDetailMonthIdx = null;
    }
    get showCmDetailModal() { return this._showCmDetailModal; }

    get cmDetailTitle() {
        if (this._cmDetailCa == null || this._cmDetailMonthIdx == null) return '';
        const labels = this.fyMonthLabels;
        const monthLabel = labels[this._cmDetailMonthIdx]?.label || '';
        return `${this._cmDetailCa}／${monthLabel}の計上内訳`;
    }

    get cmDetailRows() {
        if (!this._showCmDetailModal || !this._consultantMonthlyData) return [];
        const ca = this._cmDetailCa;
        const idx = this._cmDetailMonthIdx;
        const target = this._consultantMonthlyData.find(r => r.caName === ca);
        if (!target || !target.details) return [];
        return target.details
            .filter(d => d.monthIdx === idx)
            .sort((a, b) => (b.unitPrice || 0) - (a.unitPrice || 0))
            .map(d => {
                let dateDisplay = '';
                if (d.acceptDate) {
                    const parts = String(d.acceptDate).split('-');
                    dateDisplay = `${parseInt(parts[1])}/${parseInt(parts[2])}`;
                }
                return {
                    pipelineId: d.pipelineId,
                    studentName: d.studentName || '―',
                    companyName: d.companyName || '―',
                    unitPriceDisplay: d.unitPrice != null ? '¥' + Number(Math.round(d.unitPrice)).toLocaleString() : '―',
                    acceptDateDisplay: dateDisplay,
                    statusLabel: (d.status || '').replace(/^\d+\./, ''),
                    statusClass: this._calcStatusClass(d.status || '')
                };
            });
    }

    get cmDetailTotal() {
        const rows = this.cmDetailRows;
        if (!rows.length) return '';
        const total = rows.reduce((s, r) => {
            const v = r.unitPriceDisplay.replace(/[^\d]/g, '');
            return s + (parseInt(v, 10) || 0);
        }, 0);
        return '¥' + total.toLocaleString();
    }

    get consultantMonthlyTotals() {
        if (!this._consultantMonthlyData?.length) return [];
        const totals = Array(12).fill(0);
        this._consultantMonthlyData.forEach(r => (r.monthlyRevenue || []).forEach((v, i) => { totals[i] += v || 0; }));
        return totals.map((v, i) => ({
            key: String(i),
            revDisplay: v > 0 ? Math.round(v / 10000) + '万' : '―',
            cellClass: v > 0 ? 'gkd-cm-cell gkd-cm-cell--total' : 'gkd-cm-cell',
        }));
    }

    handleTeamYomiMonthChange(e) {
        this._selectedTeamYomiMonth = e.detail.value;
        this._teamYomiRows = [];
        this.loadTeamYomi();
    }
    handleTeamYomiCAChange(e) {
        this._selectedTeamYomiCA = e.detail.value;
        this._teamYomiRows = [];
        this.loadTeamYomi();
    }

    async handleYomiFlagToggle(e) {
        const id  = e.currentTarget.dataset.id;
        const sid = e.currentTarget.dataset.student;
        const isTab7 = e.currentTarget.dataset.tab === '7';
        const row = this._teamYomiRows.find(r => r.pipelineId === id)
                  || this._bynameRows.find(r => r.pipelineId === id);
        if (!row) return;
        const newVal = !row.yomiFlag;
        try {
            if (isTab7) {
                // Tab7: 月内ヨミ確度フラグ（非排他制御 = 複数社同時ON可）
                await setTeamYomiFlag({ pipelineId: id, flagValue: newVal });
                this._teamYomiRows = this._teamYomiRows.map(r =>
                    r.pipelineId === id ? { ...r, yomiFlag: newVal } : r
                );
            } else {
                // Tab6: ヨミ企業フラグ（排他制御 = 同学生の他社はOFF）
                await setYomiFlag({ pipelineId: id, studentId: sid, flagValue: newVal });
                this._teamYomiRows = this._teamYomiRows.map(r => {
                    if (r.studentId === sid && r.pipelineId !== id) return { ...r, yomiFlag: false };
                    if (r.pipelineId === id) return { ...r, yomiFlag: newVal };
                    return r;
                });
                this._bynameRows = this._bynameRows.map(r => {
                    if (r.studentId === sid && r.pipelineId !== id) return { ...r, yomiFlag: false };
                    if (r.pipelineId === id) return { ...r, yomiFlag: newVal };
                    return r;
                });
            }
            const msg = isTab7
                ? (newVal ? '月内ヨミ確度：高に設定（★）' : '月内ヨミ確度：解除')
                : (newVal ? 'ヨミ企業に設定（★）' : 'ヨミ企業を解除');
            this.dispatchEvent(new ShowToastEvent({ title: msg, variant: 'success' }));
        } catch(err) {
            this.dispatchEvent(new ShowToastEvent({ title: 'エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    handleTeamYomiFieldInput(e) {
        const id    = e.currentTarget.dataset.id;
        const field = e.currentTarget.dataset.field;
        const val   = e.target.value;
        this._teamYomiEditMap = { ...this._teamYomiEditMap, [id]: { ...(this._teamYomiEditMap[id] || {}), [field]: val } };
    }

    async handleTeamYomiFieldBlur(e) {
        const id    = e.currentTarget.dataset.id;
        const field = e.currentTarget.dataset.field;
        const ed    = this._teamYomiEditMap[id] || {};
        try {
            await updateTeamYomiRow({
                pipelineId:   id,
                situation:    ed.situation  !== undefined ? ed.situation  : null,
                naDateStr:    ed.naDate     !== undefined ? ed.naDate     : null,
                naDetail:     ed.naDetail   !== undefined ? ed.naDetail   : null,
                otherCompany: ed.other      !== undefined ? ed.other      : null
            });
            // ローカル反映
            this._teamYomiRows = this._teamYomiRows.map(r => r.pipelineId !== id ? r : {
                ...r,
                situation:    ed.situation  !== undefined ? ed.situation  : r.situation,
                naDate:       ed.naDate     !== undefined ? ed.naDate     : r.naDate,
                naDetail:     ed.naDetail   !== undefined ? ed.naDetail   : r.naDetail,
                otherCompany: ed.other      !== undefined ? ed.other      : r.otherCompany
            });
            const tmp = { ...this._teamYomiEditMap };
            delete tmp[id];
            this._teamYomiEditMap = tmp;
        } catch(err) {
            this.dispatchEvent(new ShowToastEvent({ title: '保存エラー', message: err.body?.message, variant: 'error' }));
        }
    }

    handleExportCSV() {
        const rows = this.teamYomiFiltered.map(r => this._processTeamRow(r));
        const headers = ['ヨミ月','学生名','卒年','担当CA','企業名','フェーズ','精度','承諾確度','確度%','加重ヨミ','ヨミチェック','現状の状況','NA日','NA詳細','他社状況'];
        const lines = [headers.join(',')];
        for (const r of rows) {
            const yomiMonthLabel = r.yomiMonth ? String(r.yomiMonth).substring(0,7) : '';
            lines.push([
                yomiMonthLabel, r.studentName || '', r.gradYear || '', r.caName || '',
                r.companyName || '', r.statusLabel || '', r.accuracyLabel || '',
                r.checkGrade, r.rateDisplay,
                r.weightedYomiDisplay, r.yomiFlag ? '✓' : '',
                (r.editingSituation || '').replace(/,/g,'、'),
                r.naDateDisplay, (r.editingNaDetail || '').replace(/,/g,'、'),
                (r.editingOther || '').replace(/,/g,'、')
            ].map(v => `"${String(v).replace(/"/g,'""')}"`).join(','));
        }
        this._downloadCsv(lines.join('\n'), 'チームヨミ管理.csv');
    }

    async loadMain() {
        this.isLoading = true;
        try {
            const periodParam = this._summaryPeriod && this._summaryPeriod !== 'all' ? this._summaryPeriod : null;
            this._data = await getGlobalKpiData({
                fiscalYear: this.selectedYear || null,
                gradYear: this.selectedGradYear || null,
                selectedMonth: this.selectedMonth || null,
                period: periodParam
            });
        } catch (e) {
            this.showError(e);
        } finally {
            this.isLoading = false;
        }
    }

    async loadPopulation() {
        this.isPopLoading = true;
        try {
            // #P2: fiscalYear を渡して年度フィルター対応
            this._popData = await getPopulationData({
                gradYear: this.selectedGradYear || null,
                fiscalYear: this.selectedYear || null
            });
        } catch (e) {
            this.showError(e);
        } finally {
            this.isPopLoading = false;
        }
    }

    async loadByname() {
        this.isBynameLoading = true;
        try {
            const recs = await getStudentPipelines({
                caName: this.selectedCA || null,
                gradYear: this.selectedGradYear || null,
                fiscalYear: this.selectedYear || null,        // 上部共通フィルタと連動
                selectedMonth: this.selectedMonth || null,    // 上部共通フィルタと連動
                yomiMonth: this._effectiveYomiMonth(this.selectedYomiMonth),
                includeInactive: this._showInactive            // 時期追い・連絡なし学生の表示トグル
            });
            this._bynameRows = recs;
            if (recs.length >= 5000) {
                this.dispatchEvent(new ShowToastEvent({
                    title: '件数上限',
                    message: '表示件数が上限（5000件）に達しています。CAや卒年でフィルターを絞り込んでください。',
                    variant: 'warning'
                }));
            }
        } catch (e) {
            this.showError(e);
        } finally {
            this.isBynameLoading = false;
        }
    }

    async loadCANames() {
        try {
            this._caNames = await getCANames();
        } catch (e) { /* silent */ }
    }

    handleOpenRecord(e) {
        const id = e.currentTarget.dataset.id;
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: { recordId: id, actionName: 'view' }
        });
    }

    showError(e) {
        const msg = (e && e.body && e.body.message) ? e.body.message : JSON.stringify(e);
        this.dispatchEvent(new ShowToastEvent({ title: 'エラー', message: msg, variant: 'error', mode: 'sticky' }));
    }

    // ─── Tab6: 一括操作・CSV ───
    get bulkSelectedCount() { return this._selectedRowIds.length; }
    get hasBulkSelection() { return this._selectedRowIds.length > 0; }
    get bulkOverLimit() { return this._selectedRowIds.length > 50; }
    get bulkApplyLabel() { return `${this._selectedRowIds.length}件に適用`; }
    get isBulkButtonDisabled() {
        return this._isBulkApplying || this._selectedRowIds.length === 0 || this._selectedRowIds.length > 50
            || (!this._bulkStatus && !this._bulkAccuracy && !this._bulkYomiMonth);
    }

    handleSelectRow(e) {
        const id = e.currentTarget.dataset.id;
        const checked = e.target.checked;
        const set = new Set(this._selectedRowIds);
        if (checked) set.add(id); else set.delete(id);
        this._selectedRowIds = Array.from(set);
    }
    handleSelectAllInGroup(e) {
        const groupKey = e.currentTarget.dataset.group;
        const checked = e.target.checked;
        const group = this._bynameRows.find(r => r.studentId === groupKey);
        // bynameRows はフラット配列なので studentId でグルーピングして処理
        const set = new Set(this._selectedRowIds);
        const groupRows = this._bynameRows.filter(r => r.studentId === groupKey);
        for (const row of groupRows) {
            if (checked) set.add(row.pipelineId);
            else set.delete(row.pipelineId);
        }
        this._selectedRowIds = Array.from(set);
    }
    handleSelectAllVisible(e) {
        const checked = e.target.checked;
        if (checked) {
            this._selectedRowIds = this._bynameRows.map(r => r.pipelineId);
        } else {
            this._selectedRowIds = [];
        }
    }
    handleClearBulkSelection() {
        this._selectedRowIds = [];
        this._bulkStatus = '';
        this._bulkAccuracy = '';
        this._bulkYomiMonth = '';
    }
    handleBulkStatusChange(e) { this._bulkStatus = e.detail.value || ''; }
    handleBulkAccuracyChange(e) { this._bulkAccuracy = e.detail.value || ''; }
    handleBulkYomiMonthChange(e) {
        // Date input → "YYYY-MM" に丸める（pipeline は ExpectedAppropriatingMonth を月初日で持つ）
        const v = e.detail.value || '';
        this._bulkYomiMonth = v ? String(v).substring(0, 7) : '';
    }
    // ネイティブ <select>/<input> 用の統合ハンドラ
    handleBulkNativeChange(e) {
        const field = e.currentTarget.dataset.field;
        const v = e.target.value || '';
        if (field === 'status') this._bulkStatus = v;
        else if (field === 'accuracy') this._bulkAccuracy = v;
        else if (field === 'yomiMonth') this._bulkYomiMonth = v ? String(v).substring(0, 7) : '';
    }
    get bulkStatusOptions() {
        return STATUS_OPTIONS.map(o => ({ ...o, selected: o.value === this._bulkStatus }));
    }
    get bulkAccuracyOptions() {
        return ACCURACY_OPTIONS.map(o => ({ ...o, selected: o.value === this._bulkAccuracy }));
    }
    async handleBulkApply() {
        if (this._selectedRowIds.length === 0) return;
        if (this._selectedRowIds.length > 50) {
            this.dispatchEvent(new ShowToastEvent({
                title: '上限超過', message: '一括更新は50件以下にしてください', variant: 'warning'
            }));
            return;
        }
        this._isBulkApplying = true;
        try {
            await bulkUpdatePipelineFields({
                pipelineIds: this._selectedRowIds,
                newStatus: this._bulkStatus || null,
                newAccuracy: this._bulkAccuracy || null,
                yomiMonthStr: this._bulkYomiMonth !== '' ? this._bulkYomiMonth : null,
                newUnitPrice: null
            });
            this.dispatchEvent(new ShowToastEvent({
                title: `${this._selectedRowIds.length}件を一括更新しました`, variant: 'success'
            }));
            this.handleClearBulkSelection();
            await this.loadByname();
        } catch (e) {
            this.showError(e);
        } finally {
            this._isBulkApplying = false;
        }
    }
    handleExportBynameCSV() {
        if (!this._bynameRows || this._bynameRows.length === 0) return;
        const headers = ['学生名','卒年','担当CA','企業名','ステータス','精度','ヨミ月','単価','加重ヨミ','面談数','ヨミ企業'];
        const lines = [headers.join(',')];
        for (const r of this._bynameRows) {
            const ymLabel = r.yomiMonth ? String(r.yomiMonth).substring(0, 7) : '';
            const unitPrice = r.unitPrice != null ? r.unitPrice : '';
            const weightedYomi = r.weightedYomiAmt != null ? Math.round(r.weightedYomiAmt) : '';
            lines.push([
                r.studentName || '', r.gradYear || '', r.caName || '',
                r.companyName || '', r.status || '', r.accuracy || '',
                ymLabel, unitPrice, weightedYomi,
                r.meetingCount != null ? r.meetingCount : '',
                r.yomiFlag ? '✓' : ''
            ].map(v => `"${String(v).replace(/"/g,'""')}"`).join(','));
        }
        this._downloadCsv(lines.join('\n'), 'CA別実績ヨミ管理.csv');
    }

    // --- 固定サマリーバー: 期間切替（all|h1|h2|q1|q2|q3|q4） ---
    handleSummaryPeriodChange(e) {
        this._summaryPeriod = e.currentTarget.dataset.period;
        // 全タブのデータを期間絞り込みで再取得
        this._referrerRows = [];
        this.loadMain();
        if (this.activeTab === 4) this.loadPopulation();
        if (this.activeTab === 5) this.loadReferrerKpi();
    }
    get summaryPeriodOptions() {
        const opts = [
            { key: 'all', label: '年度' },
            { key: 'h1',  label: 'H1' },
            { key: 'h2',  label: 'H2' },
            { key: 'q1',  label: 'Q1' },
            { key: 'q2',  label: 'Q2' },
            { key: 'q3',  label: 'Q3' },
            { key: 'q4',  label: 'Q4' },
        ];
        return opts.map(o => ({
            ...o,
            cls: 'gkd-period-btn' + (this._summaryPeriod === o.key ? ' gkd-period-btn--active' : '')
        }));
    }
    // 期間に応じたQの集計（Q1〜Q4の合計）。期間=all の場合は _data の年間値を使う
    _aggregatePeriod() {
        if (!this._data) return null;
        const qs = this._data.quarterlyBreakdown || [];
        const sum = (arr, key) => arr.reduce((s, q) => s + (q[key] || 0), 0);
        const sumStudents = (arr) => arr.reduce((s, q) => s + (q.studentCount || 0), 0); // Q間で重複ありの近似
        const pick = {
            all: null, // 年間値はtotalsから直接
            h1: qs.slice(0, 2),
            h2: qs.slice(2, 4),
            q1: qs.slice(0, 1),
            q2: qs.slice(1, 2),
            q3: qs.slice(2, 3),
            q4: qs.slice(3, 4),
        }[this._summaryPeriod];
        if (this._summaryPeriod === 'all' || !pick || pick.length === 0) {
            return {
                referrals:      this._data.totalReferrals || 0,
                accepted:       this._data.totalAccepted || 0,
                meetings:       this._data.totalMeetings || 0,
                studentCount:   this._data.totalStudentCount || 0,
                revenue:        this._data.totalRevenue || 0,
                bookedRevenue:  this._data.totalBookedRevenue || 0,
                weightedYomi:   this._data.totalWeightedYomi || 0,
            };
        }
        return {
            referrals:     sum(pick, 'referrals'),
            accepted:      sum(pick, 'accepted'),
            meetings:      sum(pick, 'meetings'),
            studentCount:  sumStudents(pick),
            revenue:       sum(pick, 'revenue'),
            bookedRevenue: sum(pick, 'bookedRevenue'),
            weightedYomi:  sum(pick, 'weightedYomi'),
        };
    }

    // --- Summary getters (期間切替対応) ---
    get totalReferrals() {
        const a = this._aggregatePeriod();
        return a ? a.referrals : 0;
    }
    get totalStudentCount() {
        const a = this._aggregatePeriod();
        return a ? a.studentCount : 0;
    }
    get totalAccepted() {
        const a = this._aggregatePeriod();
        return a ? a.accepted : 0;
    }
    get totalMeetings() {
        const a = this._aggregatePeriod();
        return a ? a.meetings : 0;
    }
    get totalOfferStudents() {
        if (!this._data || !this._data.consultantKpis) return 0;
        return this._data.consultantKpis.reduce((sum, c) => sum + (c.offerStudents || 0), 0);
    }
    get acceptanceRate() { return this._data ? this._data.acceptanceRate : 0; }
    get totalRevenueDisplay() {
        const a = this._aggregatePeriod();
        return a ? '¥' + Number(Math.round(a.revenue)).toLocaleString() : '―';
    }
    get totalBookedRevenueDisplay() {
        const a = this._aggregatePeriod();
        return a ? '¥' + Number(Math.round(a.bookedRevenue)).toLocaleString() : '―';
    }
    get totalWeightedYomiDisplay() {
        const a = this._aggregatePeriod();
        return a ? '¥' + Number(Math.round(a.weightedYomi)).toLocaleString() : '―';
    }

    // --- Tab0: サマリー（年度全体） ---
    get hasQuarterlyData() {
        return this._data && this._data.quarterlyBreakdown && this._data.quarterlyBreakdown.length > 0;
    }
    get quarterlyCards() {
        if (!this._data || !this._data.quarterlyBreakdown) return [];
        return this._data.quarterlyBreakdown.map(q => ({
            ...q,
            revenueDisplay: q.revenue != null ? '¥' + Number(Math.round(q.revenue)).toLocaleString() : '―',
            meetingToReferralRate: (q.meetings > 0 && q.referrals > 0) ? (q.referrals / q.meetings * 100).toFixed(1) + '%' : '―',
        }));
    }

    get halfYearCards() {
        if (!this._data?.quarterlyBreakdown?.length) return [];
        const [q1, q2, q3, q4] = this._data.quarterlyBreakdown;
        const make = (label, period, qa, qb) => ({
            label, period,
            referrals: (qa.referrals || 0) + (qb.referrals || 0),
            accepted:  (qa.accepted  || 0) + (qb.accepted  || 0),
            revenueDisplay: '¥' + Number(Math.round((qa.revenue || 0) + (qb.revenue || 0))).toLocaleString(),
        });
        return [make('前半期（H1）', '6〜11月', q1, q2), make('後半期（H2）', '12〜5月', q3, q4)];
    }

    get yoyCompare() {
        if (!this._data) return null;
        const prevRev = this._data.prevFyRevenue;
        if (prevRev === undefined || prevRev === null) return null;
        const cur  = { rev: this._data.totalRevenue || 0, ref: this._data.totalReferrals || 0, acc: this._data.totalAccepted || 0 };
        const prev = { rev: prevRev || 0, ref: this._data.prevFyReferrals || 0, acc: this._data.prevFyAccepted || 0 };
        const pct  = prev.rev > 0 ? Math.round((cur.rev / prev.rev - 1) * 100) : null;
        const max  = Math.max(cur.rev, prev.rev, 1);
        return {
            curLabel:       `${this.selectedYear}年度`,
            prevLabel:      `${parseInt(this.selectedYear, 10) - 1}年度`,
            curRevDisplay:  '¥' + Number(Math.round(cur.rev)).toLocaleString(),
            prevRevDisplay: prev.rev > 0 ? '¥' + Number(Math.round(prev.rev)).toLocaleString() : '前年データなし',
            growthDisplay:  pct !== null ? (pct >= 0 ? `+${pct}%` : `${pct}%`) : '―',
            growthClass:    pct === null ? '' : pct >= 0 ? 'gkd-yoy-positive' : 'gkd-yoy-negative',
            curBar:         Math.round((cur.rev / max) * 100),
            prevBar:        Math.round((prev.rev / max) * 100),
            curBarStyle:    `width:${Math.round((cur.rev / max) * 100)}%`,
            prevBarStyle:   `width:${Math.round((prev.rev / max) * 100)}%`,
            curRefDisplay:  String(cur.ref),
            prevRefDisplay: prev.ref > 0 ? String(prev.ref) : '―',
            hasPrev:        prev.rev > 0 || prev.ref > 0,
        };
    }

    // 歩留まり転換率（サマリーバー用・期間切替対応）
    get meetingToReferralPct() {
        const a = this._aggregatePeriod();
        if (!a) return '―';
        return (a.meetings > 0 && a.referrals > 0) ? (a.referrals / a.meetings * 100).toFixed(1) + '%' : '―';
    }
    get referralToAcceptedPct() {
        const a = this._aggregatePeriod();
        if (!a) return '―';
        return (a.referrals > 0) ? ((a.accepted || 0) / a.referrals * 100).toFixed(1) + '%' : '―';
    }

    // ドーナツ円グラフ（ファネル段階別）
    get donutSegments() {
        if (!this._data || !this._data.stageInfoSession) return [];
        const stages = [
            { label: '説明会以降', count: this._data.stageInfoSession || 0, color: '#0176d3' },
            { label: '書類選考以降', count: this._data.stageScreening || 0, color: '#1b96ff' },
            { label: '一次面接以降', count: this._data.stageInterview || 0, color: '#f59e0b' },
            { label: '最終面接以降', count: this._data.stageFinal || 0, color: '#e67e22' },
            { label: '内定', count: this._data.stageOffer || 0, color: '#2e844a' },
        ];
        const total = stages[0].count || 1;
        const r = 60, cx = 90, cy = 90, stroke = 28;
        const circ = 2 * Math.PI * r;
        let offset = 0;
        return stages.map(s => {
            const pct = s.count / total;
            const dash = (pct * circ).toFixed(2);
            const gap = (circ - pct * circ).toFixed(2);
            const seg = { ...s, dash, gap, offset: offset.toFixed(2), pct: Math.round(pct * 100), dotStyle: `background:${s.color}` };
            offset += pct * circ;
            return seg;
        });
    }
    get donutCircumference() { return (2 * Math.PI * 60).toFixed(2); }

    get hasFunnelData() {
        return this._data && this._data.stageInfoSession != null && this._data.stageInfoSession > 0;
    }
    get funnelStages() {
        if (!this._data) return [];
        const stages = [
            { label: '説明会以降', count: this._data.stageInfoSession || 0 },
            { label: '書類選考以降', count: this._data.stageScreening || 0 },
            { label: '一次面接以降', count: this._data.stageInterview || 0 },
            { label: '最終面接以降', count: this._data.stageFinal || 0 },
            { label: '内定',         count: this._data.stageOffer || 0 },
        ];
        const maxCount = Math.max(...stages.map(s => s.count), 1);
        const base = stages[0].count || 1;
        return stages.map(s => ({
            ...s,
            pct: base > 0 ? Math.round(s.count / base * 100) : 0,
            barStyle: `width:${Math.max((s.count / maxCount) * 100, 2).toFixed(0)}%`
        }));
    }
    get consultantTop5() {
        if (!this._data || !this._data.consultantKpis) return [];
        const sorted = [...this._data.consultantKpis]
            .sort((a, b) => (b.weightedYomi || 0) - (a.weightedYomi || 0))
            .slice(0, 5);
        const maxYomi = sorted.length > 0 ? Math.max(...sorted.map(c => c.weightedYomi || 0), 1) : 1;
        return sorted.map((c, i) => {
            const pct = maxYomi > 0 ? Math.max(((c.weightedYomi || 0) / maxYomi) * 100, 2).toFixed(1) : 0;
            const rankClassMap = ['gkd-rank-1', 'gkd-rank-2', 'gkd-rank-3', 'gkd-rank-other', 'gkd-rank-other'];
            return {
                ...c,
                rank: i + 1,
                rankClass: 'gkd-top5-rank ' + (rankClassMap[i] || 'gkd-rank-other'),
                weightedYomiDisplay: c.weightedYomi != null ? '¥' + Number(Math.round(c.weightedYomi)).toLocaleString() : '―',
                barStyle: `width:${pct}%`,
            };
        });
    }

    // --- Tab1: 月別トレンド ---
    get hasMonthlyData() {
        return this._data && this._data.monthlyTrend && this._data.monthlyTrend.length > 0;
    }
    get trendGridLines() {
        if (!this.hasMonthlyData) return [];
        const max = Math.max(...this._data.monthlyTrend.map(m => m.count), 1);
        const step = Math.ceil(max / 4) || 1;
        const lines = [];
        for (let v = 0; v <= max; v += step) {
            const y = (15 + (1 - v / max) * 110).toFixed(1);
            lines.push({ y, labelY: (parseFloat(y) + 3).toFixed(1), value: v, label: 'g' + v });
        }
        return lines;
    }
    get trendBarItems() {
        if (!this.hasMonthlyData) return [];
        const items = this._data.monthlyTrend;
        const max = Math.max(...items.map(m => m.count), 1);
        const gap = 565 / items.length;
        const bw = Math.max(Math.floor(gap * 0.55), 6);
        return items.map((item, idx) => {
            const h = Math.max((item.count / max) * 110, 2).toFixed(1);
            const x = (44 + idx * gap + (gap - bw) / 2).toFixed(1);
            const y = (125 - parseFloat(h)).toFixed(1);
            const cx = (parseFloat(x) + bw / 2).toFixed(1);
            return {
                label: item.label, count: item.count, x, y, width: bw, height: h, centerX: cx,
                countY: (parseFloat(y) - 3).toFixed(1),
                countLabel: item.label + '-c', monthLabel: item.label + '-m',
            };
        });
    }

    // --- Tab2: 担当者別 ---
    get hasConsultantData() {
        return this._data && this._data.consultantKpis && this._data.consultantKpis.length > 0;
    }
    get consultantRows() {
        if (!this.hasConsultantData) return [];
        return [...this._data.consultantKpis]
            .sort((a, b) => (b.referrals || 0) - (a.referrals || 0))
            .map(c => ({
                name: c.name,
                totalStudents: c.totalStudents || 0,
                validStudents: c.validStudents || 0,
                validRate: c.validRate || '0%',
                meetingCount: c.meetingCount || 0,
                meetingToReferralRate: c.meetingToReferralRate || '―',
                referrals: c.referrals,
                sessionParticipated: c.sessionParticipated || 0,
                offerCount: c.offerCount || 0,
                accepted: c.accepted,
                declinedAfterAccept: c.declinedAfterAccept || 0,
                declineAfterAcceptRate: c.declineAfterAcceptRate || '―',
                acceptanceRate: c.acceptanceRate,
                offerStudents: c.offerStudents || 0,
                avgAcceptPriceDisplay: c.avgAcceptPrice ? '¥' + Number(Math.round(c.avgAcceptPrice)).toLocaleString() : '―',
                revenueDisplay: '¥' + Number(Math.round(c.revenue || 0)).toLocaleString(),
                bookedRevenueDisplay: '¥' + Number(Math.round(c.bookedRevenue || 0)).toLocaleString(),
                yomiDisplay: '¥' + Number(Math.round(c.weightedYomi || 0)).toLocaleString(),
            }));
    }
    // 未着手案件
    get staleStudentDisplay() {
        const v = this._data && this._data.staleStudentCount;
        return v != null ? v.toLocaleString() + '人' : '―';
    }
    // 平均承諾サイクル日数
    get avgAcceptCycleDisplay() {
        const v = this._data && this._data.avgAcceptCycleDays;
        return v != null && v > 0 ? Number(v).toFixed(1) : '―';
    }
    // ヨミ確度別積み上げバー
    get yomiAccuracyBars() {
        if (!this._data) return [];
        const segs = [
            { label: 'S', count: this._data.yomiCntS || 0, color: '#2e844a' },
            { label: 'A', count: this._data.yomiCntA || 0, color: '#0176d3' },
            { label: 'B', count: this._data.yomiCntB || 0, color: '#7c3aed' },
            { label: 'C', count: this._data.yomiCntC || 0, color: '#f59e0b' },
            { label: 'D', count: this._data.yomiCntD || 0, color: '#dc2626' },
            { label: '未', count: this._data.yomiCntNone || 0, color: '#94a3b8' },
        ];
        const total = segs.reduce((s, x) => s + x.count, 0) || 1;
        return segs.filter(s => s.count > 0).map(s => {
            const pct = (s.count / total * 100).toFixed(1);
            return {
                label: s.label,
                count: s.count,
                title: `${s.label}: ${s.count}件 (${pct}%)`,
                cls: 'gkd-yomi-seg',
                style: `flex:${s.count}; background:${s.color}; min-width:${s.count > 0 ? 40 : 0}px;`
            };
        });
    }
    // 全体平均承諾単価 = 計上売上 / (承諾数 + 承諾後辞退)
    get avgAcceptPriceDisplay() {
        const total = (this.totalAccepted || 0) + (this.totalDeclinedAfterAccept || 0);
        if (total === 0) return '―';
        const bookedRev = (this._data && this._data.totalBookedRevenue) || 0;
        return '¥' + Number(Math.round(bookedRev / total)).toLocaleString();
    }
    get totalDeclinedAfterAccept() {
        if (!this.hasConsultantData) return 0;
        return this._data.consultantKpis.reduce((s, c) => s + (c.declinedAfterAccept || 0), 0);
    }
    get totalDeclineAfterAcceptRate() {
        const total = this.totalAccepted + this.totalDeclinedAfterAccept;
        return total > 0 ? (this.totalDeclinedAfterAccept / total * 100).toFixed(1) + '%' : '―';
    }
    get totalSessionParticipated() {
        if (!this.hasConsultantData) return 0;
        return this._data.consultantKpis.reduce((s, c) => s + (c.sessionParticipated || 0), 0);
    }
    get totalOfferCount() {
        if (!this.hasConsultantData) return 0;
        return this._data.consultantKpis.reduce((s, c) => s + (c.offerCount || 0), 0);
    }
    // 合計行用: 面談学生ベースの承諾率（承諾合計 ÷ 面談学生合計）
    get acceptanceRateOverMeeting() {
        const mtg = this.totalMeetings || 0;
        return mtg > 0 ? (this.totalAccepted / mtg * 100).toFixed(1) + '%' : '―';
    }

    // --- Tab3: 企業別 ---
    get hasCompanyData() {
        return this._data && this._data.companyKpis && this._data.companyKpis.length > 0;
    }
    get companyRows() {
        if (!this.hasCompanyData) return [];
        const pct = (n, d) => d > 0 ? (n / d * 100).toFixed(1) + '%' : '―';
        return [...this._data.companyKpis]
            .sort((a, b) => (b.referrals || 0) - (a.referrals || 0))
            .map(c => ({
                companyName: c.companyName,
                referrals: c.referrals || 0,
                sessionParticipated: c.sessionParticipated || 0,
                interview1Pass: c.interview1Pass || 0,
                interview2Pass: c.interview2Pass || 0,
                interview3Pass: c.interview3Pass || 0,
                finalPass: c.finalPass || 0,
                offerCount: c.offerCount || 0,
                accepted: c.accepted || 0,
                sessionRate:    pct(c.sessionParticipated, c.referrals),
                if1Rate:        pct(c.interview1Pass, c.sessionParticipated),
                if2Rate:        pct(c.interview2Pass, c.interview1Pass),
                if3Rate:        pct(c.interview3Pass, c.interview2Pass),
                finalRate:      pct(c.finalPass, c.interview3Pass),
                offerRate:      pct(c.offerCount, c.finalPass),
                acceptRate:     pct(c.accepted, c.offerCount),
                acceptanceRate: c.acceptanceRate,
                revenueDisplay: '¥' + Number(Math.round(c.revenue || 0)).toLocaleString(),
                bookedRevenueDisplay: '¥' + Number(Math.round(c.bookedRevenue || 0)).toLocaleString(),
                yomiDisplay: '¥' + Number(Math.round(c.weightedYomi || 0)).toLocaleString(),
            }));
    }
    handleExportCompanyCSV() {
        if (!this.hasCompanyData) return;
        const headers = ['企業名','紹介数','説明会参加','参加率','1次参加','通過率','2次参加','通過率','3次参加','通過率','最終参加','通過率','内定','内定率','承諾','承諾率','全体承諾率','実売上','計上売上','加重ヨミ'];
        const lines = [headers.join(',')];
        for (const r of this.companyRows) {
            const stripYen = (s) => String(s).replace(/[¥,]/g, '');
            lines.push([
                r.companyName, r.referrals, r.sessionParticipated, r.sessionRate,
                r.interview1Pass, r.if1Rate, r.interview2Pass, r.if2Rate,
                r.interview3Pass, r.if3Rate, r.finalPass, r.finalRate,
                r.offerCount, r.offerRate, r.accepted, r.acceptRate,
                r.acceptanceRate,
                stripYen(r.revenueDisplay), stripYen(r.bookedRevenueDisplay), stripYen(r.yomiDisplay)
            ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','));
        }
        this._downloadCsv(lines.join('\n'), `企業別KPI_${this.selectedYear || 'all'}.csv`);
    }

    get companyTotals() {
        if (!this.hasCompanyData) return null;
        const rows = this._data.companyKpis;
        const totalRef = rows.reduce((s, r) => s + (r.referrals || 0), 0);
        const totalAcc = rows.reduce((s, r) => s + (r.accepted  || 0), 0);
        const totalRev  = rows.reduce((s, r) => s + (r.revenue  || 0), 0);
        const totalYomi = rows.reduce((s, r) => s + (r.weightedYomi || 0), 0);
        return {
            totalRef, totalAcc,
            accRate: totalRef > 0 ? (totalAcc / totalRef * 100).toFixed(1) + '%' : '―',
            revenueDisplay: '¥' + Number(Math.round(totalRev)).toLocaleString(),
            yomiDisplay:    '¥' + Number(Math.round(totalYomi)).toLocaleString(),
        };
    }

    // --- Tab4: 母集団 ---
    get totalStudents() { return this._popData ? this._popData.totalStudents : 0; }
    get validStudents() { return this._popData ? this._popData.validStudents : 0; }
    get athleteStudents() { return this._popData ? this._popData.athleteStudents : 0; }
    get validStudentRate() {
        const t = this._popData && this._popData.totalStudents;
        const v = this._popData && this._popData.validStudents;
        return t ? (v / t * 100).toFixed(1) : '0';
    }
    get athleteRate() {
        const t = this._popData && this._popData.totalStudents;
        const a = this._popData && this._popData.athleteStudents;
        return t ? (a / t * 100).toFixed(1) : '0';
    }
    get routeBreakdown() {
        if (!this._popData || !this._popData.routeBreakdown) return [];
        const max = Math.max(...this._popData.routeBreakdown.map(r => r.count), 1);
        return this._popData.routeBreakdown.map(r => ({
            ...r, barStyle: `width:${Math.max((r.count / max) * 100, 2).toFixed(0)}%`
        }));
    }
    get gradYearBreakdown() {
        if (!this._popData || !this._popData.gradYearBreakdown) return [];
        const max = Math.max(...this._popData.gradYearBreakdown.map(r => r.count), 1);
        return this._popData.gradYearBreakdown.map(r => ({
            ...r, barStyle: `width:${Math.max((r.count / max) * 100, 2).toFixed(0)}%`
        }));
    }
    get rankBreakdown() {
        if (!this._popData || !this._popData.rankBreakdown) return [];
        const max = Math.max(...this._popData.rankBreakdown.map(r => r.count), 1);
        // ランク順にソート: S+, S, S-, A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, E, F
        const rankOrder = ['S+','S','S-','A+','A','A-','B+','B','B-','C+','C','C-','D+','D','D-','E','F'];
        const sorted = [...this._popData.rankBreakdown].sort((a, b) => {
            const ai = rankOrder.indexOf(a.label);
            const bi = rankOrder.indexOf(b.label);
            return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
        });
        return sorted.map(r => ({
            ...r, barStyle: `width:${Math.max((r.count / max) * 100, 2).toFixed(0)}%`
        }));
    }
    get rankBarItems() {
        // SVGグラフ用（横棒）
        if (!this.rankBreakdown || this.rankBreakdown.length === 0) return [];
        const max = Math.max(...this.rankBreakdown.map(r => r.count), 1);
        return this.rankBreakdown.map((r, i) => {
            const barW = Math.max((r.count / max) * 260, 2).toFixed(1);
            const y = 14 + i * 22;
            return { ...r, key: 'rank-' + i, y, barW: Number(barW), cntX: Number(barW) + 38, textY: y + 11 };
        });
    }
    get rankSvgHeight() {
        return Math.max(this.rankBreakdown.length * 22 + 10, 60);
    }
    get rankSvgViewbox() {
        return `0 0 310 ${this.rankSvgHeight}`;
    }

    // --- Tab6: CA別実績ヨミ管理 ---
    // フィルタ連鎖のみ（option生成・グルーピングを含まない軽量版）
    get bynameFilteredRows() {
        let sourceRows = this._bynameRows;
        if (this.selectedPhase && this._phaseStatusMap[this.selectedPhase]) {
            const validStatuses = new Set(this._phaseStatusMap[this.selectedPhase]);
            sourceRows = sourceRows.filter(r => validStatuses.has(r.status));
        }
        if (this._onlyYomiFlag) {
            sourceRows = sourceRows.filter(r => r.yomiFlag === true);
        }
        if (this._studentNameQuery) {
            const q = this._studentNameQuery.toLowerCase();
            sourceRows = sourceRows.filter(r => {
                const name = (r.studentName || '').replace(/[\s　]+/g, '').toLowerCase();
                return name.includes(q);
            });
        }
        if (this._companyQuery) {
            const q = this._companyQuery.toLowerCase();
            sourceRows = sourceRows.filter(r =>
                (r.companyName || '').replace(/[\s　]+/g, '').toLowerCase().includes(q)
            );
        }
        if (this._selectedAccuracyFilter) {
            sourceRows = sourceRows.filter(r => r.accuracy === this._selectedAccuracyFilter);
        }
        return sourceRows;
    }
    get hasBynameData() { return this.bynameFilteredRows.length > 0; }
    get bynameNeedsFilter() { return !this.selectedCA && !this.selectedGradYear && this._bynameRows.length === 0; }
    get showDetailModal() { return this._showDetailModal; }
    get detailPipelineId() { return this._detailPipelineId; }
    // KPIバー: _bynameRows を1パスで集計（バージョンキャッシュで多重バインドの再計算を防止）
    get bynameKpi() {
        if (this._bynameKpiCache && this._bynameKpiCacheVer === this._bynameVersion) {
            return this._bynameKpiCache;
        }
        const rows = this._bynameRows;
        const INTERVIEW_ACTIVE = new Set([
            '008.一次面接参加予定','009.一次面接通過','012.二次面接参加予定','013.二次面接通過',
            '016.三次面接参加予定','017.三次面接通過','020.最終面接参加予定','021.最終面接通過'
        ]);
        const studentIds = new Set();
        const meetingSeen = new Set();
        let interviewCount = 0, offerCount = 0, acceptedCount = 0;
        let yomiTotal = 0, totalMeetings = 0, realRevenue = 0;
        for (const r of rows) {
            const key = r.studentId || r.pipelineId;
            studentIds.add(key);
            if (!meetingSeen.has(key)) {
                meetingSeen.add(key);
                totalMeetings += r.meetingCount || 0;
            }
            if (INTERVIEW_ACTIVE.has(r.status)) interviewCount++;
            if (r.status === '024.内定') offerCount++;
            if (r.status === '025.内定承諾') {
                acceptedCount++;
                realRevenue += r.unitPrice || 0;
            }
            yomiTotal += r.weightedYomiAmt || 0;
        }
        const ref = rows.length;
        const yen = (n) => '¥' + Number(Math.round(n)).toLocaleString();
        const result = {
            pipelineCount: ref,
            studentCount: studentIds.size,
            interviewCount,
            offerCount,
            acceptedCount,
            yomiTotal: yen(yomiTotal),
            totalMeetings,
            realRevenue: yen(realRevenue),
            mtgToRefRate: totalMeetings ? (ref / totalMeetings * 100).toFixed(1) + '%' : '―',
            refToAcceptRate: ref ? (acceptedCount / ref * 100).toFixed(1) + '%' : '―',
        };
        this._bynameKpiCache = result;
        this._bynameKpiCacheVer = this._bynameVersion;
        return result;
    }

    // 学生ごとにグルーピング（P6: studentId をキーにして同名異人を分離）
    get bynameGrouped() {
        const map = new Map();
        // フィルタ連鎖は bynameFilteredRows に集約（hasBynameData と共有）
        const sourceRows = this.bynameFilteredRows;
        const selectedSet = new Set(this._selectedRowIds);
        const processedRows = sourceRows.map(r => {
            const st = r.status || '';
            const statusClass = this._calcStatusClass(st);

            const isSelected = selectedSet.has(r.pipelineId);

            const acc = r.accuracy || '';
            let accuracyClass = 'gkd-accuracy';
            if (acc === 'S') accuracyClass += ' gkd-acc-s';
            else if (acc === 'A') accuracyClass += ' gkd-acc-a';
            else if (acc === 'B') accuracyClass += ' gkd-acc-b';
            else if (acc === 'C') accuracyClass += ' gkd-acc-c';

            // P5（JST）: "YYYY-MM-DD" をUTCずれなしでパース
            let yomiMonthDisplay = '―';
            if (r.yomiMonth) {
                const parts = String(r.yomiMonth).split('-');
                yomiMonthDisplay = `${parts[0]}/${parseInt(parts[1], 10)}月`;
            }

            // P13: 単価nullのときヨミを「―」表示
            const hasPrice = r.unitPrice != null;

            return {
                ...r,
                statusLabel: st.replace(/^\d+\./, ''),
                statusClass,
                accuracyClass,
                caName: r.caName || '―',
                companyDisplay: r.companyName || '（求人票未設定）',  // P11
                unitPriceDisplay: hasPrice ? '¥' + Number(Math.round(r.unitPrice)).toLocaleString() : '―',
                yomiDisplay: hasPrice ? '¥' + Number(Math.round(r.weightedYomiAmt || 0)).toLocaleString() : '―',
                yomiMonthDisplay,
                meetingCountDisplay: r.meetingCount != null ? r.meetingCount : '―',
                // ★ヨミチェック ボタンの表示クラス（黄色塗りつぶし or グレー）
                yomiFlagClass: r.yomiFlag ? 'gkd-yomi-flag gkd-yomi-flag--on' : 'gkd-yomi-flag',
                rowClass: isSelected ? 'gkd-row-selected' : '',
                isSelected,
                yomiMonthValue: r.yomiMonth ? String(r.yomiMonth).substring(0, 7) : '',
            };
        });

        // P6: studentId をグルーピングキーに使用（同名異人を分離）
        processedRows.forEach(r => {
            const key = r.studentId || r.pipelineId;
            if (!map.has(key)) {
                map.set(key, {
                    key: 'grp-' + key,
                    studentName: r.studentName || '不明',
                    caName: r.caName,
                    gradYear: r.gradYear,
                    meetingDate: r.meetingDate || null,
                    pipelines: [],
                    totalYomi: 0,
                    realRevenue: 0,
                    acceptedCount: 0
                });
            }
            const grp = map.get(key);
            // 面談日は学生単位で同一だが、念のため最新を保持
            if (r.meetingDate && (!grp.meetingDate || r.meetingDate > grp.meetingDate)) {
                grp.meetingDate = r.meetingDate;
            }
            grp.pipelines.push(r);
            // P13: 単価ありの場合のみヨミ合計に加算
            if (r.unitPrice != null) grp.totalYomi += r.weightedYomiAmt || 0;
            if (r.status === '025.内定承諾' && r.unitPrice != null) grp.realRevenue += r.unitPrice;
            if (r.status === '025.内定承諾') grp.acceptedCount += 1;
        });

        const groups = [...map.values()].map(g => {
            const acceptRateNum = g.pipelines.length > 0
                ? (g.acceptedCount / g.pipelines.length * 100)
                : -1;
            const pct = g.pipelines.length > 0 ? acceptRateNum.toFixed(1) + '%' : '―';
            let meetingDateDisplay = '―';
            if (g.meetingDate) {
                const parts = String(g.meetingDate).split('-');
                if (parts.length === 3) meetingDateDisplay = `${parts[0]}/${parseInt(parts[1],10)}/${parseInt(parts[2],10)}`;
            }
            return {
                ...g,
                totalYomiDisplay: '¥' + Number(Math.round(g.totalYomi)).toLocaleString(),
                realRevenueDisplay: g.realRevenue > 0 ? '¥' + Number(Math.round(g.realRevenue)).toLocaleString() : '―',
                acceptRateDisplay: pct,
                acceptRateNum,
                meetingDateDisplay,
                pipelineCount: g.pipelines.length
            };
        });

        // ソート適用
        const field = this._sortField || 'meetingDate';
        const dir = this._sortDir === 'asc' ? 1 : -1;
        groups.sort((a, b) => {
            let av, bv;
            switch (field) {
                case 'meetingDate':
                    av = a.meetingDate ? String(a.meetingDate) : '';
                    bv = b.meetingDate ? String(b.meetingDate) : '';
                    // 空は常に最後
                    if (!av && !bv) return 0;
                    if (!av) return 1;
                    if (!bv) return -1;
                    return av < bv ? -dir : av > bv ? dir : 0;
                case 'totalYomi': av = a.totalYomi || 0; bv = b.totalYomi || 0; return (av - bv) * dir;
                case 'realRevenue': av = a.realRevenue || 0; bv = b.realRevenue || 0; return (av - bv) * dir;
                case 'acceptRate': av = a.acceptRateNum; bv = b.acceptRateNum; return (av - bv) * dir;
                case 'studentName':
                    av = a.studentName || ''; bv = b.studentName || '';
                    return av < bv ? -dir : av > bv ? dir : 0;
                default: return 0;
            }
        });
        return groups;
    }

    // --- 評価フィールドブレークダウン ---
    get evaluationBreakdown() {
        if (!this._popData || !this._popData.evaluationBreakdown) return [];
        return this._popData.evaluationBreakdown.map(ef => ({
            ...ef,
            key: 'ef-' + ef.fieldName,
            items: (ef.items || []).map((item, idx) => ({
                ...item,
                key: 'efitem-' + ef.fieldName + '-' + idx,
                barStyle: `width:${Math.max((item.count / Math.max(...(ef.items || []).map(x => x.count), 1)) * 100, 2).toFixed(0)}%`
            }))
        }));
    }

    // --- 月別トレンド拡張（売上・承諾） ---
    get trendTableRows() {
        if (!this.hasMonthlyData) return [];
        return this._data.monthlyTrend.map(m => ({
            label: m.label,
            count: m.count,
            meetings: m.meetings || 0,
            accepted: m.accepted || 0,
            revenueDisplay: m.revenue ? '¥' + Number(Math.round(m.revenue)).toLocaleString() : '―',
            accRate: m.count > 0 ? ((m.accepted || 0) / m.count * 100).toFixed(1) + '%' : '―',
            mtgToRefRate: (m.meetings > 0 && m.count > 0) ? (m.count / m.meetings * 100).toFixed(1) + '%' : '―',
        }));
    }
    get trendTotalRow() {
        if (!this.hasMonthlyData) return null;
        const rows = this._data.monthlyTrend;
        const totalCount = rows.reduce((s, m) => s + (m.count || 0), 0);
        const totalAcc = rows.reduce((s, m) => s + (m.accepted || 0), 0);
        const totalRev = rows.reduce((s, m) => s + (m.revenue || 0), 0);
        const totalMtg = rows.reduce((s, m) => s + (m.meetings || 0), 0);
        return {
            count: totalCount,
            meetings: totalMtg,
            accepted: totalAcc,
            revenueDisplay: '¥' + Number(Math.round(totalRev)).toLocaleString(),
            accRate: totalCount > 0 ? (totalAcc / totalCount * 100).toFixed(1) + '%' : '―',
            mtgToRefRate: (totalMtg > 0 && totalCount > 0) ? (totalCount / totalMtg * 100).toFixed(1) + '%' : '―',
        };
    }

    // 月次面談数バーチャート
    get trendMeetingBarItems() {
        if (!this.hasMonthlyData) return [];
        const items = this._data.monthlyTrend;
        const max = Math.max(...items.map(m => m.meetings || 0), 1);
        const gap = 565 / items.length;
        const bw = Math.max(Math.floor(gap * 0.55), 6);
        return items.map((item, idx) => {
            const h = max > 0 ? Math.max(((item.meetings || 0) / max) * 110, (item.meetings > 0 ? 2 : 0)).toFixed(1) : '0';
            const x = (44 + idx * gap + (gap - bw) / 2).toFixed(1);
            const y = (125 - parseFloat(h)).toFixed(1);
            const cx = (parseFloat(x) + bw / 2).toFixed(1);
            return {
                key: 'mtg-' + idx,
                label: item.label, meetings: item.meetings || 0,
                x, y, width: bw, height: h, centerX: cx,
                countY: (parseFloat(y) - 3).toFixed(1),
            };
        });
    }
    get trendMeetingGridLines() {
        if (!this.hasMonthlyData) return [];
        const max = Math.max(...this._data.monthlyTrend.map(m => m.meetings || 0), 1);
        const step = Math.ceil(max / 4) || 1;
        const lines = [];
        for (let v = 0; v <= max; v += step) {
            const y = (15 + (1 - v / max) * 110).toFixed(1);
            lines.push({ key: 'mg' + v, y, labelY: (parseFloat(y) + 3).toFixed(1), value: v });
        }
        return lines;
    }

    // --- 月次売上SVGバーチャート ---
    get trendRevBarItems() {
        if (!this.hasMonthlyData) return [];
        const items = this._data.monthlyTrend;
        const max = Math.max(...items.map(m => m.revenue || 0), 1);
        const gap = 565 / items.length;
        const bw = Math.max(Math.floor(gap * 0.55), 6);
        return items.map((item, idx) => {
            const h = max > 0 ? Math.max(((item.revenue || 0) / max) * 90, (item.revenue > 0 ? 2 : 0)).toFixed(1) : '0';
            const x = (44 + idx * gap + (gap - bw) / 2).toFixed(1);
            const y = (110 - parseFloat(h)).toFixed(1);
            return {
                key: 'rev-' + idx,
                label: item.label,
                x, y, width: bw, height: h,
                centerX: (parseFloat(x) + bw / 2).toFixed(1),
                countY: (parseFloat(y) - 3).toFixed(1),
                hasRev: (item.revenue || 0) > 0,
                revLabel: item.revenue ? '¥' + (Math.round(item.revenue / 10000)) + '万' : '',
            };
        });
    }
    get trendRevSvgGridLines() {
        if (!this.hasMonthlyData) return [];
        const max = Math.max(...this._data.monthlyTrend.map(m => m.revenue || 0), 1);
        const step = Math.ceil(max / 4 / 100000) * 100000 || 1;
        const lines = [];
        for (let v = 0; v <= max; v += step) {
            const y = (110 - (v / max) * 90).toFixed(1);
            const lbl = v >= 1000000 ? (v / 1000000).toFixed(1) + 'M' : (v / 10000) + '万';
            lines.push({ y, labelY: (parseFloat(y) + 3).toFixed(1), label: lbl, key: 'rl-' + v });
        }
        return lines;
    }
}