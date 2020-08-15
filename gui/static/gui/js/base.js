const BasicsUrl = "/api/v1/basics/";
const GlobalTypesUrl = BasicsUrl + "global-types/";
const GlobalCodesUrl = BasicsUrl + "global-codes/";

const EquipCategoryUrl = BasicsUrl + "equips-category/";
// const EquipCategoryUrl = BasicsUrl + "equips-category-list/";
const EquipTypeGlobalUrl = BasicsUrl + "global-codes/?class_name=设备类型";
const EquipProcessGlobalUrl = BasicsUrl + "global-codes/?class_name=工序";
const EquipLevelGlobalUrl = BasicsUrl + "global-codes/?class_name=产地";
const StateGlobalUrl = BasicsUrl + "global-codes/?class_name=胶料状态";
const SiteGlobalUrl = BasicsUrl + "global-codes/?class_name=产地";
const StageGlobalUrl = BasicsUrl + "global-codes/?class_name=胶料段次";
const DevTypeGlobalUrl = BasicsUrl + "global-codes/?class_name=炼胶机类型";

const EquipUrl = BasicsUrl + "equips/";

const SystemUrl = "/api/v1/system/";
const PersonnelsUrl = SystemUrl + "personnels/";
const PermissionUrl = SystemUrl + "permission/";
const GroupUrl = SystemUrl + "group_extension/";
const UsersByGroupUrl = SystemUrl + "personnels_groups/";
const WorkSchedulesUrl = BasicsUrl + "work_schedules/";
const GroupAddUserUrl = SystemUrl + "group_add_user/";
const MaterialsUrl = "/api/v1/recipe/materials/";
const ProductInfosUrl = "/api/v1/recipe/product-infos/";
const ValidateVersionsUrl = "/api/v1/recipe/validate-versions";
const CopyProductInfosUrl = "/api/v1/recipe/copy-product-infos/";
// 胶料配料标准管理接口
const RubberMaterialUrl = "/api/v1/recipe/product-batching/";
// 胶料配料标准管理——选择胶料编码与段次接口
const RubberStageUrl = "/api/v1/recipe/product-stages/";
const PreBatchInfoUrl = "/api/v1/recipe/pre-batch-info/";
const ProductRecipeUrl = "/api/v1/recipe/product-recipe/";

const ProductBatching = "/api/v1/plan/product-batching-day-plans/";
const MaterialRequisitionsCopy = "/api/v1/plan/product-batching-day-plans-copy/";
// 领料计划接口
const MaterialDemanded = "/api/v1/plan/material-demanded-apiview/";
const MaterialRequisitions = "/api/v1/plan/material-requisition-classes/"
//胶料日计划
const ProductDayPlans = "/api/v1/plan/product-day-plans/";

const PalletFeedBacksUrl = "/api/v1/production/pallet-feedbacks/";
//胶料日计划
const ProductDayPlansUrl = "/api/v1/plan/product-day-plans/";

//排产配料小料日计划---选择胶料
const RubberSelectUrl = "/api/v1/plan/product-batching-day-plan-manycreate/";
const PlanScheduleUrl = "/api/v1/basics/plan-schedule/";

const ProductActualUrl = "/api/v1/production/product-actual/"
//密炼实绩
const ProductDayPlansCopyUrl = "/api/v1/plan/product-day-plans-copy/";
const PalletFeedbacksUrl = "/api/v1/production/pallet-feedbacks/"
const TrainsFeedbacksUrl = "/api/v1/production/trains-feedbacks/"

var BaseMixin = {

    data: function () {
        return {

            pageSize: 10,
            tableDataTotal: 0,
            tableDataUrl: "",
            tableData: [],
            currentPage: 1,
            getParams: {},

            defaultActive: "",
            formLabelWidth: "120px",
            openeds: ["2", "3", "4", "5"],
        }
    },
    created: function () {

        for (var key in Routes) {
            if (Routes[key] === window.location.pathname)
                this.defaultActive = key;
        }
        this.currentChange(1)
    },
    methods: {

        beforeGetData: function () {
        },
        afterGetData: function () {
        },
        getFirstPage: function () {

            this.currentPage = 1;
            this.currentChange(1);
        },
        currentChange: function (page) {

            this.beforeGetData();
            this.getParams["page"] = page;
            this.tableData = [];
            const app = this;
            axios.get(this.tableDataUrl, {

                params: this.getParams
            }).then(function (response) {

                if (app.tableDataTotal !== response.data.count) {
                    app.tableDataTotal = response.data.count;
                }
                app.tableData = response.data.results;
                app.afterGetData();

            }).catch(function (error) {
                this.$message.error(error);
            })
        },
        select: function (index, indexPath) {

            window.location = Routes[index];
        },
        boolFormatter: function (flag) {

            return flag ? "Y" : "N"
        }
    }
};
