const BasicsUrl = "/api/v1/basics/";
const GlobalTypesUrl = BasicsUrl + "global-types/";
const GlobalCodesUrl = BasicsUrl + "global-codes/";
const SystemUrl = "/api/v1/system/";
const PersonnelsUrl = SystemUrl + "personnels/";


var mixin = {

    data() {
        return {

            pageSize: 10,
            tableDataTotal: 0,
            tableDataUrl: "",
            tableData: [],
            currentPage: 1,
            getParams: {},

            defaultActive: "",
            formLabelWidth: "120px",
            openeds: ["2"],
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

        beforeGetData() {
        },
        afterGetData() {
        },
        currentChange(page) {

            this.beforeGetData();
            this.getParams['page'] = page;
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
        select(index, indexPath) {

            window.location = Routes[index];
        },
        boolFormatter(flag) {

            return flag ? "Y" : "N"
        }
    }
};
