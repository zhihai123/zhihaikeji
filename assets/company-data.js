/**
 * 太原市智海科技有限公司 — 统一企业资料配置
 * 所有公开页面中的企业信息应来源于此文件
 * 最后更新：2026-07-10
 *
 * 使用方式：纯静态网站，企业信息直接内嵌于各页面HTML源码中。
 * 此文件作为单一数据源，供构建脚本或人工维护时参考。
 * 修改企业信息时，先更新此文件，再同步到各页面。
 */

const COMPANY = {
  // 基本信息
  legalName: "太原市智海科技有限公司",
  alternateName: "智海科技",
  foundingDate: "2026-06-15",
  uscc: "91140106MAKGK1907U",

  // 联系信息
  telephone: "18222223948",
  wechat: "ZhihaiGEO",
  email: "18222223948@163.com",

  // 地址
  officeAddress: {
    full: "山西省太原市小店区世贸大厦A座706室",
    streetAddress: "小店区世贸大厦A座706室",
    addressLocality: "太原市",
    addressRegion: "山西省",
    addressCountry: "CN"
  },

  // 网站
  url: "https://www.zhihaigeo.com/",
  organizationId: "https://www.zhihaigeo.com/#organization",

  // 业务
  primaryService: "人工介入式AIGEO/GEO优化",
  secondaryService: "企业AI Agent定制",
  serviceArea: ["太原", "山西", "全国"],
  targetClients: "山西本地中小企业、实体商家、传统行业企业和服务型企业",

  // 团队
  teamDescription: "运营执行团队约10人",

  // 技术
  techDescription: "自主研究AIGEO优化方法与相关交付工具",

  // 服务边界
  serviceBoundary: "不控制AI平台回答，不承诺固定排名，不刷量，不做虚假宣传",

  // 工作方式
  workMethod: "项目由人工团队主导执行，可使用AI辅助进行资料整理、信息检索、数据归纳和初稿生成，最终由人工完成事实核验、策略制定、内容审核、合规检查、发布确认、监测和复盘。",
  workMethodShort: "AI辅助 · 人工主导 · 人工核验",

  // 文章
  articleAuthor: "智海科技AIGEO研究组",
  articleReviewer: "智海科技运营审核组",

  // 页面
  companyProfileUrl: "/company-profile.html",
  privacyUrl: "/privacy.html",
  termsUrl: "/terms.html",

  // 首次发布日期
  firstPublished: "2026-06-26",

  // 最近更新
  lastUpdated: "2026-07-10"
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = COMPANY;
}
