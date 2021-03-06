#coding:utf-8

from apps.database.databaseCase import *
from apps.aliexpress.smtAPI import *
from apps.jingdong.jdAPI import *
from apps.alibaba.alibabaAPI import *

import random

class Home():
    def on_get(self, req, resp):
        result = {'method':req.method,'success':True}
        resp.body = json.dumps(result, ensure_ascii=False)


class CheckSMTOrder():
    def on_get(self, req, resp):
        params = req._params

        if params.has_key('storeId'):
            storeId = params['storeId']
        else:
            storeId = ''
        if params.has_key('status'):
            status = params['status']
        else:
            status = ''
        if params.has_key('createDateStart'):
            createDateStart = params['createDateStart']
        else:
            createDateStart = ''
        if params.has_key('createDateEnd'):
            createDateEnd = params['createDateEnd']
        else:
            createDateEnd = ''

        data = dict()

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        appList = db.appList.find({'platform': 'aliexpress', 'apiInfo.status': 1})

        if storeId == '':
            # appKey = aList[random.randint(0,len(aList)-1)]
            app = appList[random.randint(0, appList.count() - 1)]
        else:
            app = db.appList.find_one({'storeId': storeId})

        data['error'] = []
        if app != None:

            api = ALIEXPRESS(app)

            # 判断API是否可用
            if api.status > 0:

                total = 0
                addCount = 0
                updateCount = 0

                # statusList = ['WAIT_SELLER_SEND_GOODS','PLACE_ORDER_SUCCESS','IN_CANCEL','IN_ISSUE','RISK_CONTROL','WAIT_BUYER_ACCEPT_GOODS']
                statusList = status.split(',')

                for s in statusList:

                    option = dict()
                    option['pageSize'] = '50'
                    option['page'] = '1'
                    option['orderStatus'] = s

                    if s == 'WAIT_BUYER_ACCEPT_GOODS' and createDateStart == '':
                        option['createDateStart'] = (datetime.datetime.now() + datetime.timedelta(days=-10)).strftime(
                            '%Y-%m-%d %H:%M:%S')
                        option['createDateEnd'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        option['createDateStart'] = createDateStart
                        option['createDateEnd'] = createDateEnd

                    c = api.getOrderList(option)

                    try:
                        result = json.loads(c)

                        ol = result['orderList']
                        total += result['totalItem']

                        updateTime = datetime.datetime.now()
                        for od in ol:

                            order = db.orderList.find_one({'orderId': str(od['orderId'])})
                            if order:

                                item = od

                                newData = dict()
                                newData['orderStatus'] = item['orderStatus']
                                newData['frozenStatus'] = item['frozenStatus']
                                newData['issueStatus'] = item['issueStatus']
                                newData['fundStatus'] = item['fundStatus']
                                if item.has_key('logisticsStatus'):
                                    newData['logisticsStatus'] = item['logisticsStatus']
                                newData['updateTime'] = updateTime
                                if item.has_key('timeoutLeftTime'):
                                    newData['timeoutLeftTime'] = item['timeoutLeftTime']
                                else:
                                    newData['timeoutLeftTime'] = None
                                if item.has_key('leftSendGoodMin'):
                                    newData['leftSendGoodMin'] = item['leftSendGoodMin']
                                elif order.has_key('leftSendGoodMin'):
                                    newData['leftSendGoodMin'] = None
                                if item.has_key('leftSendGoodHour'):
                                    newData['leftSendGoodHour'] = item['leftSendGoodHour']
                                elif order.has_key('leftSendGoodHour'):
                                    newData['leftSendGoodHour'] = None
                                if item.has_key('leftSendGoodDay'):
                                    newData['leftSendGoodDay'] = item['leftSendGoodDay']
                                elif order.has_key('leftSendGoodDay'):
                                    newData['leftSendGoodDay'] = None

                                if item.has_key('memo'):
                                    newData['memo'] = item['memo']

                                if item.has_key('gmtPayTime'):
                                    newData['gmtPayTime'] = datetime.datetime.strptime(item['gmtPayTime'][:14],
                                                                                       '%Y%m%d%H%M%S')

                                db.orderList.update({'orderId': str(item['orderId'])}, {'$set': newData})

                                # print(newData)

                                updateCount += 1
                            else:
                                item = od
                                item['orderId'] = str(item['orderId'])
                                item['createTime'] = datetime.datetime.now()
                                item['updateTime'] = updateTime
                                item['apiStoreID'] = app['apiStoreID']
                                item['storeInfo'] = {'storeId': app['storeId'], 'cnName': app['cnName'],
                                                     'enName': app['enName'], "operator": app["operator"],
                                                     'dealPeron': app['dealPeron']}
                                item['platform'] = app['platform']

                                item['dealStatus'] = 'WAIT_SYSTEM_CHECK'
                                item['oprationLog'] = []
                                item['weight'] = None
                                item['totalCost'] = None
                                item['totalProfit'] = None
                                item['isLock'] = 0
                                item['type'] = 0
                                item['isShelve'] = 0
                                item['isShelve'] = 0
                                item['errorMsg'] = None
                                item['isMakeup'] = 0
                                item['reSendReason'] = 0
                                item['isMergeOrder'] = 0
                                item['isSplitOrder'] = 0
                                item['hasMessage'] = 0
                                item['isDelivery'] = 0
                                item['checkName'] = 0
                                item['orderMemo'] = []
                                item['labels'] = []
                                item['pickStatus'] = 0

                                item['gmtCreate'] = datetime.datetime.strptime(od['gmtCreate'][:14], '%Y%m%d%H%M%S')

                                if od.has_key('gmtPayTime'):
                                    item['gmtPayTime'] = datetime.datetime.strptime(od['gmtPayTime'][:14],
                                                                                    '%Y%m%d%H%M%S')

                                for sku in item['productList']:
                                    sku['productId'] = str(sku['productId'])
                                    sku['childId'] = str(sku['childId'])
                                    sku['orderId'] = str(sku['orderId'])
                                    sku['skuId'] = None
                                    sku['skuAttr'] = None
                                    sku['purchaseNo'] = None
                                    sku['weight'] = None
                                    sku['pickStatus'] = 0

                                db.orderList.insert(item)
                                addCount += 1

                        if int(result['totalItem']) > int(option['pageSize']):
                            totalPage = int(result['totalItem']) / int(option['pageSize'])
                            mod = int(result['totalItem']) % int(option['pageSize'])
                            if mod > 0:
                                totalPage += 1

                            pl = range(2, totalPage + 1)
                            for page in pl:
                                # print(page)
                                option['page'] = str(page)
                                # print(option)
                                m = api.getOrderList(option)
                                moreUpdateTime = datetime.datetime.now()
                                try:
                                    moreOrder = json.loads(m)
                                    moreOrderList = moreOrder['orderList']

                                    for orderItem in moreOrderList:

                                        order = db.orderList.find_one({'orderId': str(orderItem['orderId'])})
                                        if order:

                                            moreItem = orderItem

                                            newData = dict()
                                            newData['orderStatus'] = moreItem['orderStatus']
                                            newData['frozenStatus'] = moreItem['frozenStatus']
                                            newData['issueStatus'] = moreItem['issueStatus']
                                            newData['fundStatus'] = moreItem['fundStatus']
                                            if moreItem.has_key('logisticsStatus'):
                                                newData['logisticsStatus'] = moreItem['logisticsStatus']
                                            newData['updateTime'] = moreUpdateTime
                                            if moreItem.has_key('timeoutLeftTime'):
                                                newData['timeoutLeftTime'] = moreItem['timeoutLeftTime']
                                            else:
                                                newData['timeoutLeftTime'] = None
                                            if moreItem.has_key('leftSendGoodMin'):
                                                newData['leftSendGoodMin'] = moreItem['leftSendGoodMin']
                                            elif order.has_key('leftSendGoodMin'):
                                                newData['leftSendGoodMin'] = None
                                            if moreItem.has_key('leftSendGoodHour'):
                                                newData['leftSendGoodHour'] = moreItem['leftSendGoodHour']
                                            elif order.has_key('leftSendGoodHour'):
                                                newData['leftSendGoodHour'] = None
                                            if moreItem.has_key('leftSendGoodDay'):
                                                newData['leftSendGoodDay'] = moreItem['leftSendGoodDay']
                                            elif order.has_key('leftSendGoodDay'):
                                                newData['leftSendGoodDay'] = None

                                            if moreItem.has_key('memo'):
                                                newData['memo'] = moreItem['memo']

                                            if moreItem.has_key('gmtPayTime'):
                                                newData['gmtPayTime'] = datetime.datetime.strptime(
                                                    moreItem['gmtPayTime'][:14], '%Y%m%d%H%M%S')

                                            db.orderList.update({'orderId': str(moreItem['orderId'])},
                                                                {'$set': newData})

                                            updateCount += 1
                                        else:
                                            moreItem = orderItem
                                            moreItem['orderId'] = str(moreItem['orderId'])
                                            moreItem['createTime'] = datetime.datetime.now()
                                            moreItem['updateTime'] = moreUpdateTime
                                            moreItem['apiStoreID'] = app['apiStoreID']
                                            moreItem['storeInfo'] = {'storeId': app['storeId'], 'cnName': app['cnName'],
                                                                     'enName': app['enName'],
                                                                     "operator": app["operator"],
                                                                     'dealPeron': app['dealPeron']}
                                            moreItem['platform'] = app['platform']

                                            moreItem['dealStatus'] = 'WAIT_SYSTEM_CHECK'
                                            moreItem['oprationLog'] = []
                                            moreItem['weight'] = None
                                            moreItem['totalCost'] = None
                                            moreItem['totalProfit'] = None
                                            moreItem['isLock'] = 0
                                            moreItem['type'] = 0
                                            moreItem['isShelve'] = 0
                                            moreItem['isShelve'] = 0
                                            moreItem['errorMsg'] = None
                                            moreItem['isMakeup'] = 0
                                            moreItem['reSendReason'] = 0
                                            moreItem['isMergeOrder'] = 0
                                            moreItem['isSplitOrder'] = 0
                                            moreItem['hasMessage'] = 0
                                            moreItem['isDelivery'] = 0
                                            moreItem['checkName'] = 0
                                            moreItem['orderMemo'] = []
                                            moreItem['labels'] = []
                                            moreItem['pickStatus'] = 0

                                            moreItem['gmtCreate'] = datetime.datetime.strptime(
                                                orderItem['gmtCreate'][:14],
                                                '%Y%m%d%H%M%S')

                                            if orderItem.has_key('gmtPayTime'):
                                                moreItem['gmtPayTime'] = datetime.datetime.strptime(
                                                    orderItem['gmtPayTime'][:14],
                                                    '%Y%m%d%H%M%S')

                                            for sku in moreItem['productList']:
                                                sku['productId'] = str(sku['productId'])
                                                sku['childId'] = str(sku['childId'])
                                                sku['orderId'] = str(sku['orderId'])
                                                sku['skuId'] = None
                                                sku['skuAttr'] = None
                                                sku['purchaseNo'] = None
                                                sku['weight'] = None
                                                sku['pickStatus'] = 0

                                            db.orderList.insert(moreItem)
                                            addCount += 1

                                except Exception as e:
                                    data['error'].append(
                                        {'storeId': app['storeId'], 'errMsg': str(e), 'data': m, 'options': option})

                    except Exception as e:
                        # print(e)
                        data['error'].append(
                            {'storeId': app['storeId'], 'errMsg': str(e), 'data': c, 'options': option})

                data['success'] = True
                data['data'] = {"total": total, "addCount": addCount, 'updateCount': updateCount}

            else:
                data['success'] = False
                data['error'].append(
                    {'storeId': storeId, 'errMsg': 'APP Unavailable', 'options': {'orderStatus': status}})
        else:
            data['success'] = False
            data['error'].append({'storeId': storeId, 'errMsg': 'APP Unavailable', 'options': {'orderStatus': status}})

        resp.body = json.dumps(data, ensure_ascii=False)

class ChekSMTProduct():
    def on_get(self, req, resp):
        params = req._params
        if params.has_key('storeId'):
            storeId = params['storeId']
        else:
            storeId = ''
        if params.has_key('status'):
            status = params['status']
        else:
            status = 'onSelling'

        data = dict()

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        appList = db.appList.find({'platform': 'aliexpress', 'apiInfo.status': 1})

        if storeId == '':
            # appKey = aList[random.randint(0,len(aList)-1)]
            app = appList[random.randint(0, appList.count() - 1)]
        else:
            app = db.appList.find_one({'storeId': storeId})

        data['error'] = []
        if app != None:

            api = ALIEXPRESS(app)

            # 判断API是否可用
            if api.status > 0:

                total = 0
                addCount = 0
                updateCount = 0

                # statusList = ['onSelling','offline','auditing','editingRequired']
                statusList = status.split(',')

                for s in statusList:

                    option = dict()
                    option['pageSize'] = '100'
                    option['currentPage'] = '1'
                    option['productStatusType'] = s

                    c = api.getProductInfoList(option)

                    try:
                        result = json.loads(c)

                        if result['productCount'] > 0:

                            pl = result['aeopAEProductDisplayDTOList']
                            total += result['productCount']

                            updateTime = datetime.datetime.now()

                            # db.productList.update({},{'$set':{'isDelete':1}})

                            for pd in pl:

                                product = db.productList.find_one({'productId': str(pd['productId'])})
                                if product:

                                    newData = pd
                                    newData['productId'] = str(pd['productId'])
                                    newData['isDelete'] = 0
                                    newData['productStatusType'] = s
                                    newData['updateTime'] = updateTime

                                    if product['subject'] != pd['subject']:
                                        newData['checkTitleStatus'] = 'waitCheck'

                                    newData['wsOfflineDate'] = datetime.datetime.strptime(pd['wsOfflineDate'][:14],
                                                                                          '%Y%m%d%H%M%S')
                                    newData['gmtCreate'] = datetime.datetime.strptime(pd['gmtCreate'][:14],
                                                                                      '%Y%m%d%H%M%S')
                                    newData['gmtModified'] = datetime.datetime.strptime(pd['gmtModified'][:14],
                                                                                        '%Y%m%d%H%M%S')

                                    db.productList.update({'productId': str(pd['productId'])}, {'$set': newData})

                                    # print(newData)

                                    updateCount += 1
                                else:
                                    item = pd
                                    item['productId'] = str(pd['productId'])
                                    item['createTime'] = datetime.datetime.now()
                                    item['updateTime'] = updateTime
                                    item['apiStoreID'] = app['apiStoreID']
                                    item['storeInfo'] = {'storeId': app['storeId'], 'cnName': app['cnName'],
                                                         'enName': app['enName'], "operator": app["operator"],
                                                         'dealPeron': app['dealPeron']}
                                    item['platform'] = app['platform']

                                    item['isDelete'] = 0
                                    item['productStatusType'] = s
                                    item['checkTitleStatus'] = 'waitCheck'

                                    item['labels'] = []
                                    item['riskWords'] = []
                                    item['isNew'] = 1

                                    item['gmtCreate'] = datetime.datetime.strptime(pd['gmtCreate'][:14], '%Y%m%d%H%M%S')
                                    item['gmtModified'] = datetime.datetime.strptime(pd['gmtModified'][:14],
                                                                                     '%Y%m%d%H%M%S')
                                    item['wsOfflineDate'] = datetime.datetime.strptime(pd['wsOfflineDate'][:14],
                                                                                       '%Y%m%d%H%M%S')

                                    db.productList.insert(item)
                                    addCount += 1

                            if int(result['productCount']) > int(option['pageSize']):
                                totalPage = int(result['totalPage'])

                                pl = range(2, totalPage + 1)
                                for page in pl:
                                    option['currentPage'] = str(page)
                                    m = api.getProductInfoList(option)
                                    moreUpdateTime = datetime.datetime.now()
                                    try:
                                        moreProduct = json.loads(m)

                                        moreProductList = moreProduct['aeopAEProductDisplayDTOList']

                                        for productItem in moreProductList:

                                            mp = db.productList.find_one({'productId': str(productItem['productId'])})
                                            if mp:

                                                newData = productItem
                                                newData['productId'] = str(productItem['productId'])
                                                newData['isDelete'] = 0
                                                newData['productStatusType'] = s
                                                newData['updateTime'] = moreUpdateTime

                                                if mp['subject'] != productItem['subject']:
                                                    newData['checkTitleStatus'] = 'waitCheck'

                                                newData['wsOfflineDate'] = datetime.datetime.strptime(
                                                    productItem['wsOfflineDate'][:14], '%Y%m%d%H%M%S')
                                                newData['gmtCreate'] = datetime.datetime.strptime(
                                                    productItem['gmtCreate'][:14], '%Y%m%d%H%M%S')
                                                newData['gmtModified'] = datetime.datetime.strptime(
                                                    productItem['gmtModified'][:14], '%Y%m%d%H%M%S')

                                                db.productList.update({'productId': str(productItem['productId'])},
                                                                      {'$set': newData})

                                                updateCount += 1
                                            else:
                                                moreItem = productItem
                                                moreItem['productId'] = str(moreItem['productId'])

                                                moreItem['createTime'] = datetime.datetime.now()
                                                moreItem['updateTime'] = moreUpdateTime
                                                moreItem['apiStoreID'] = app['apiStoreID']
                                                moreItem['storeInfo'] = {'storeId': app['storeId'],
                                                                         'cnName': app['cnName'],
                                                                         'enName': app['enName'],
                                                                         "operator": app["operator"],
                                                                         'dealPeron': app['dealPeron']}
                                                moreItem['platform'] = app['platform']

                                                moreItem['isDelete'] = 0
                                                moreItem['productStatusType'] = s
                                                moreItem['checkTitleStatus'] = 'waitCheck'

                                                moreItem['labels'] = []
                                                moreItem['riskWords'] = []
                                                moreItem['isNew'] = 1

                                                moreItem['gmtCreate'] = datetime.datetime.strptime(
                                                    productItem['gmtCreate'][:14], '%Y%m%d%H%M%S')
                                                moreItem['gmtModified'] = datetime.datetime.strptime(
                                                    productItem['gmtModified'][:14], '%Y%m%d%H%M%S')
                                                moreItem['wsOfflineDate'] = datetime.datetime.strptime(
                                                    productItem['wsOfflineDate'][:14], '%Y%m%d%H%M%S')

                                                db.productList.insert(moreItem)
                                                addCount += 1

                                    except Exception as e:
                                        # print(e)
                                        data['error'].append(
                                            {'storeId': app['storeId'], 'errMsg': str(e), 'options': option})


                    except Exception as e:
                        # print(e)
                        data['error'].append({'storeId': app['storeId'], 'errMsg': str(e), 'options': option})

                data['success'] = True
                data['data'] = {"total": total, "addCount": addCount, 'updateCount': updateCount}

            else:
                data['success'] = False
                data['error'].append({'storeId': storeId, 'errMsg': 'APP Unavailable', 'options': {'status': status}})
        else:
            data['success'] = False
            data['error'].append({'storeId': storeId, 'errMsg': 'APP Unavailable', 'options': {'status': status}})

        resp.body = json.dumps(data, ensure_ascii=False)

class RefreshSMTOrderStatus():
    def on_get(self, req, resp):
        data = dict()
        params = req._params
        if params.has_key('items'):
            items = params['items']
        else:
            items = ''

        ol = json.loads(items)

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        data['error'] = []
        for (k, v) in ol.items():
            app = db.appList.find_one({'storeId': k})
            if app != None:
                api = ALIEXPRESS(app)
                if api.status > 0:
                    ids = v.strip(',').split(',')
                    for id in ids:
                        c = api.getOrderBaseInfo(id)
                        try:
                            d = json.loads(c)
                            if d != {}:
                                newData = d
                                newData['gmtModified'] = datetime.datetime.strptime(newData['gmtModified'],
                                                                                    '%Y-%m-%d %H:%M:%S')
                                newData['gmtCreate'] = datetime.datetime.strptime(newData['gmtCreate'],
                                                                                  '%Y-%m-%d %H:%M:%S')

                                if newData['orderStatus'] == 'FINISH' or newData[
                                    'orderStatus'] == 'WAIT_BUYER_ACCEPT_GOODS' or newData[
                                    'orderStatus'] == 'FUND_PROCESSING':
                                    newData['timeoutLeftTime'] = None
                                    newData['leftSendGoodMin'] = None
                                    newData['leftSendGoodDay'] = None
                                    newData['leftSendGoodHour'] = None

                                db.orderList.update({'orderId': id}, {'$set': newData})
                        except:
                            print(c)
                            data['error'].append({'id': id, 'errMsg': str(c)})
                else:
                    data['error'].append({'storeId': k, 'errMsg': '接口不可用'})

        data['success'] = True
        data['errCount'] = len(data['error'])

        resp.body = json.dumps(data, ensure_ascii=False)

class RefreshSMTOrderInfos():
    def on_get(self, req, resp):
        data = dict()
        params = req._params
        if params.has_key('items'):
            items = params['items']
        else:
            items = ''

        ol = json.loads(items)

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        data['error'] = []

        for (k, v) in ol.items():
            app = db.appList.find_one({'storeId': k})
            if app != None:
                api = ALIEXPRESS(app)
                if api.status > 0:
                    ids = v.strip(',').split(',')
                    for id in ids:
                        c = api.getOrderDetail(id)
                        if c != 'null':
                            orderInfo = json.loads(c)
                            orderData = db.orderList.find_one({'orderId': id})
                            newData = dict()
                            if not orderData.has_key('buyerInfo'):
                                newData['buyerInfo'] = orderInfo['buyerInfo']
                            if not orderData.has_key('receiptAddress'):
                                newData['receiptAddress'] = orderInfo['receiptAddress']
                            if not orderData.has_key('sellerOperatorLoginId'):
                                newData['sellerOperatorLoginId'] = orderInfo['sellerOperatorLoginId']
                            if orderInfo.has_key('gmtPaySuccess'):
                                newData['gmtPaySuccess'] = datetime.datetime.strptime(orderInfo['gmtPaySuccess'][:14],
                                                                                      '%Y%m%d%H%M%S')
                            if not orderData.has_key('paymentType') and orderInfo.has_key('paymentType'):
                                newData['paymentType'] = orderInfo['paymentType']
                            if not orderData.has_key('initOderAmount'):
                                newData['initOderAmount'] = orderInfo['initOderAmount']
                            if not orderData.has_key('logisticsAmount'):
                                newData['logisticsAmount'] = orderInfo['logisticsAmount']
                            if not orderData.has_key('orderAmount'):
                                newData['orderAmount'] = orderInfo['orderAmount']
                            if not orderData.has_key('isPhone'):
                                newData['isPhone'] = orderInfo['isPhone']

                            if not orderData.has_key('childOrderExtInfoList'):
                                childOrderExtInfoList = orderInfo['childOrderExtInfoList']
                                newChild = []
                                for child in childOrderExtInfoList:
                                    child['productId'] = str(child['productId'])
                                    child['sku'] = json.loads(child['sku'])['sku']
                                    newChild.append(child)

                                newData['childOrderExtInfoList'] = newChild

                            # 子订单包含状态
                            if not orderData.has_key('childOrderList'):
                                childOrderList = orderInfo['childOrderList']
                                newChild = []
                                for child in childOrderList:
                                    child['id'] = str(child['id'])
                                    child['productId'] = str(child['productId'])
                                    child['productAttributes'] = json.loads(child['productAttributes'])
                                    newChild.append(child)

                                newData['childOrderList'] = newChild

                            newData['issueInfo'] = orderInfo['issueInfo']
                            newData['issueStatus'] = orderInfo['issueStatus']
                            newData['loanInfo'] = orderInfo['loanInfo']
                            newData['logisticInfoList'] = orderInfo['logisticInfoList']
                            if orderInfo.has_key('logisticsStatus'):
                                newData['logisticsStatus'] = orderInfo['logisticsStatus']
                            newData['oprLogDtoList'] = orderInfo['oprLogDtoList']
                            newData['orderMsgList'] = orderInfo['orderMsgList']
                            newData['orderStatus'] = orderInfo['orderStatus']
                            newData['frozenStatus'] = orderInfo['frozenStatus']
                            newData['fundStatus'] = orderInfo['fundStatus']
                            newData['gmtModified'] = orderInfo['gmtModified']

                            if newData['orderStatus'] == 'FINISH' or newData[
                                'orderStatus'] == 'WAIT_BUYER_ACCEPT_GOODS' or newData[
                                'orderStatus'] == 'FUND_PROCESSING':
                                newData['timeoutLeftTime'] = None
                                newData['leftSendGoodMin'] = None
                                newData['leftSendGoodDay'] = None
                                newData['leftSendGoodHour'] = None

                            # print(newData)
                            db.orderList.update({'orderId': id}, {'$set': newData})

                        else:

                            data['error'].append({'id': id, 'errMsg': '找不到该订单'})


                else:
                    data['error'].append({'storeId': k, 'errMsg': '接口不可用'})

        data['success'] = True
        data['errCount'] = len(data['error'])

        resp.body = json.dumps(data, ensure_ascii=False)


class CheckSMTNewOrderInfos():
    def on_get(self, req, resp):
        data = dict()
        params = req._params
        if params.has_key('storeId'):
            storeId = params['storeId']
        else:
            storeId = ''
        if params.has_key('key'):
            key = params['key']
        else:
            key = 'receiptAddress'
        if params.has_key('pageSize'):
            pageSize = params['pageSize']
        else:
            pageSize = '50'

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        try:
            pageSize = int(pageSize)
        except:
            pageSize = 50

        data['error'] = []

        appList = db.appList.find({'platform': 'aliexpress', 'apiInfo.status': 1})

        if storeId == '':
            # appKey = aList[random.randint(0,len(aList)-1)]
            app = appList[random.randint(0, appList.count() - 1)]
        else:
            app = db.appList.find_one({'storeId': storeId})

        data['error'] = []
        data['count'] = 0

        if app != None:

            if app != None:
                api = ALIEXPRESS(app)
                if api.status > 0:
                    # ol = db.orderList.find({key: {'$exists':0}, 'storeInfo.storeId': app['storeId']}, {'orderId': 1}).limit(pageSize)
                    updateFilter = {'storeInfo.storeId': app['storeId'],
                                    'updateTime': {'$lt': datetime.datetime.now() + datetime.timedelta(hours=-1),
                                                   'orderStatus': {
                                                       '$in': ['WAIT_SELLER_SEND_GOODS', 'PLACE_ORDER_SUCCESS',
                                                               'IN_CANCEL', 'SELLER_PART_SEND_GOODS', 'FUND_PROCESSING',
                                                               'IN_ISSUE', 'RISK_CONTROL']}}}
                    ol = db.orderList.find(
                        {'$or': [{key: {'$exists': 0}, 'storeInfo.storeId': app['storeId']}, updateFilter]},
                        {'orderId': 1}).limit(pageSize)
                    for o in ol:
                        id = o['orderId']
                        c = api.getOrderDetail(id)
                        if c != 'null':
                            orderInfo = json.loads(c)
                            orderData = db.orderList.find_one({'orderId': id})
                            newData = dict()
                            if not orderData.has_key('buyerInfo'):
                                newData['buyerInfo'] = orderInfo['buyerInfo']
                            if not orderData.has_key('receiptAddress'):
                                newData['receiptAddress'] = orderInfo['receiptAddress']
                            if not orderData.has_key('sellerOperatorLoginId'):
                                newData['sellerOperatorLoginId'] = orderInfo['sellerOperatorLoginId']
                            if orderInfo.has_key('gmtPaySuccess'):
                                newData['gmtPaySuccess'] = datetime.datetime.strptime(orderInfo['gmtPaySuccess'][:14],
                                                                                      '%Y%m%d%H%M%S')
                            if orderInfo.has_key('gmtPaySuccess'):
                                newData['gmtPayTime'] = datetime.datetime.strptime(orderInfo['gmtPaySuccess'][:14],
                                                                                   '%Y%m%d%H%M%S')
                            if not orderData.has_key('paymentType') and orderInfo.has_key('paymentType'):
                                newData['paymentType'] = orderInfo['paymentType']
                            if not orderData.has_key('initOderAmount'):
                                newData['initOderAmount'] = orderInfo['initOderAmount']
                            if not orderData.has_key('logisticsAmount'):
                                newData['logisticsAmount'] = orderInfo['logisticsAmount']
                            if not orderData.has_key('orderAmount'):
                                newData['orderAmount'] = orderInfo['orderAmount']
                            if not orderData.has_key('isPhone'):
                                newData['isPhone'] = orderInfo['isPhone']

                            if not orderData.has_key('childOrderExtInfoList'):
                                childOrderExtInfoList = orderInfo['childOrderExtInfoList']
                                newChild = []
                                for child in childOrderExtInfoList:
                                    child['productId'] = str(child['productId'])
                                    child['sku'] = json.loads(child['sku'])['sku']
                                    newChild.append(child)

                                newData['childOrderExtInfoList'] = newChild

                            # 子订单包含状态
                            if not orderData.has_key('childOrderList'):
                                childOrderList = orderInfo['childOrderList']
                                newChild = []
                                for child in childOrderList:
                                    child['id'] = str(child['id'])
                                    child['productId'] = str(child['productId'])
                                    child['productAttributes'] = json.loads(child['productAttributes'])
                                    newChild.append(child)

                                newData['childOrderList'] = newChild

                            newData['issueInfo'] = orderInfo['issueInfo']
                            newData['issueStatus'] = orderInfo['issueStatus']
                            newData['loanInfo'] = orderInfo['loanInfo']
                            newData['logisticInfoList'] = orderInfo['logisticInfoList']
                            if orderInfo.has_key('logisticsStatus'):
                                newData['logisticsStatus'] = orderInfo['logisticsStatus']
                            newData['oprLogDtoList'] = orderInfo['oprLogDtoList']
                            newData['orderMsgList'] = orderInfo['orderMsgList']
                            newData['orderStatus'] = orderInfo['orderStatus']
                            newData['frozenStatus'] = orderInfo['frozenStatus']
                            newData['fundStatus'] = orderInfo['fundStatus']
                            newData['gmtModified'] = orderInfo['gmtModified']

                            if newData['orderStatus'] == 'FINISH' or newData[
                                'orderStatus'] == 'WAIT_BUYER_ACCEPT_GOODS' or newData[
                                'orderStatus'] == 'FUND_PROCESSING':
                                newData['timeoutLeftTime'] = None
                                newData['leftSendGoodMin'] = None
                                newData['leftSendGoodDay'] = None
                                newData['leftSendGoodHour'] = None

                            # print(newData)
                            db.orderList.update({'orderId': id}, {'$set': newData})
                            data['count'] += 1

                        else:

                            data['error'].append({'id': id, 'errMsg': '找不到该订单'})


                else:
                    data['error'].append({'storeId': app['storeId'], 'errMsg': '接口不可用'})

        data['success'] = True
        data['errCount'] = len(data['error'])

        resp.body = json.dumps(data, ensure_ascii=False)

class RefreshSMTProductStatus():
    def on_get(self, req, resp):
        data = dict()
        params = req._params
        if params.has_key('items'):
            items = params['items']
        else:
            items = ''
        ol = json.loads(items)

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        data['error'] = []
        for (k, v) in ol.items():
            app = db.appList.find_one({'storeId': k})
            if app != None:
                api = ALIEXPRESS(app)
                if api.status > 0:
                    ids = v.strip(',').split(',')
                    for id in ids:
                        c = api.getProductStatusById(id)
                        try:
                            d = json.loads(c)
                            if d.has_key('status'):
                                newData = dict()
                                newData['updateTime'] = datetime.datetime.now()

                                if d['status'] == 'refuse':
                                    newData['productStatusType'] = 'editingRequired'
                                elif d['status'] == 'auditing':
                                    newData['productStatusType'] = 'auditing'

                                db.productList.update({'productId': id}, {'$set': newData})

                            elif d.has_key('error_message'):
                                if d['error_code'] == '10004000':
                                    db.productList.update({'productId': id},
                                                          {'$set': {'isDelete': 1, 'productStatusType': 'delete'}})

                                data['error'].append({'id': id, 'errMsg': d['error_message']})

                        except:
                            print(c)
                            data['error'].append({'id': id, 'errMsg': str(c)})
                else:
                    data['error'].append({'storeId': k, 'errMsg': '接口不可用'})

        data['success'] = True
        data['errCount'] = len(data['error'])

        resp.body = json.dumps(data, ensure_ascii=False)

class RefreshSMTProductInfos():
    def on_get(self, req, resp):
        data = dict()
        params = req._params
        if params.has_key('items'):
            items = params['items']
        else:
            items = ''

        ol = json.loads(items)

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        data['error'] = []

        for (k, v) in ol.items():
            app = db.appList.find_one({'storeId': k})
            if app != None:
                api = ALIEXPRESS(app)
                if api.status > 0:
                    ids = v.strip(',').split(',')
                    for id in ids:
                        c = api.getProductById(id)
                        try:
                            d = json.loads(c)
                            productData = db.productList.find_one({'productId': id})

                            if d.has_key('success') and d['success']:
                                d['productId'] = str(d['productId'])
                                d['aeopNationalQuoteConfiguration'] = json.loads(d['aeopNationalQuoteConfiguration'])
                                d['gmtModified'] = datetime.datetime.strptime(d['gmtModified'][:14], '%Y%m%d%H%M%S')
                                d['wsOfflineDate'] = datetime.datetime.strptime(d['wsOfflineDate'][:14], '%Y%m%d%H%M%S')
                                d['gmtCreate'] = datetime.datetime.strptime(d['gmtCreate'][:14], '%Y%m%d%H%M%S')
                                if d.has_key('couponStartDate'):
                                    d['couponStartDate'] = datetime.datetime.strptime(d['couponStartDate'][:14],
                                                                                      '%Y%m%d%H%M%S')
                                if d.has_key('couponEndDate'):
                                    d['couponEndDate'] = datetime.datetime.strptime(d['couponEndDate'][:14],
                                                                                    '%Y%m%d%H%M%S')

                                # 如果修改了标题,重新检查标题
                                if productData['subject'] != d['subject']:
                                    d['checkTitleStatus'] = 'waitCheck'

                                # print(newData)
                                db.productList.update({'productId': id}, {'$set': d})
                            elif d.has_key('error_message'):
                                if d['error_code'] == '10004000':
                                    db.productList.update({'productId': id},
                                                          {'$set': {'isDelete': 1, 'productStatusType': 'delete'}})
                                data['error'].append({'id': id, 'errMsg': d['error_message']})

                        except Exception as e:
                            data['error'].append({'id': id, 'errMsg': str(e)})

                else:
                    data['error'].append({'storeId': k, 'errMsg': '接口不可用'})

        data['success'] = True
        data['errCount'] = len(data['error'])

        resp.body = json.dumps(data, ensure_ascii=False)


class RefreshSMTNewProductInfos():
    def on_get(self, req, resp):
        data = dict()
        params = req._params
        if params.has_key('storeId'):
            storeId = params['storeId']
        else:
            storeId = ''

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        appList = db.appList.find({'platform': 'aliexpress', 'apiInfo.status': 1})

        if storeId == '':
            # appKey = aList[random.randint(0,len(aList)-1)]
            app = appList[random.randint(0, appList.count() - 1)]
        else:
            app = db.appList.find_one({'storeId': storeId})

        data['error'] = []
        data['count'] = 0

        if app != None:

            api = ALIEXPRESS(app)

            # 判断API是否可用
            if api.status > 0:
                pl = db.productList.find({'aeopAeProductSKUs': {'$exists': 0}, 'storeInfo.storeId': app['storeId']},
                                         {'productId': 1}).limit(30)
                for p in pl:
                    id = p['productId']
                    c = api.getProductById(id)
                    try:
                        d = json.loads(c)
                        productData = db.productList.find_one({'productId': id})

                        if d.has_key('success') and d['success']:
                            d['productId'] = str(d['productId'])
                            d['aeopNationalQuoteConfiguration'] = json.loads(d['aeopNationalQuoteConfiguration'])
                            d['gmtModified'] = datetime.datetime.strptime(d['gmtModified'][:14], '%Y%m%d%H%M%S')
                            d['wsOfflineDate'] = datetime.datetime.strptime(d['wsOfflineDate'][:14], '%Y%m%d%H%M%S')
                            d['gmtCreate'] = datetime.datetime.strptime(d['gmtCreate'][:14], '%Y%m%d%H%M%S')
                            if d.has_key('couponStartDate'):
                                d['couponStartDate'] = datetime.datetime.strptime(d['couponStartDate'][:14],
                                                                                  '%Y%m%d%H%M%S')
                            if d.has_key('couponEndDate'):
                                d['couponEndDate'] = datetime.datetime.strptime(d['couponEndDate'][:14], '%Y%m%d%H%M%S')

                            # 如果修改了标题,重新检查标题
                            if productData['subject'] != d['subject']:
                                d['checkTitleStatus'] = 'waitCheck'

                            # print(newData)
                            db.productList.update({'productId': id}, {'$set': d})
                            data['count'] += 1
                        elif d.has_key('error_message'):
                            if d['error_code'] == '10004000':
                                db.productList.update({'productId': id},
                                                      {'$set': {'isDelete': 1, 'productStatusType': 'delete'}})
                                data['count'] += 1
                            data['error'].append({'id': id, 'errMsg': d['error_message']})

                    except Exception as e:
                        data['error'].append({'id': id, 'errMsg': str(e)})

            else:
                data['error'].append({'storeId': app['storeId'], 'errMsg': '接口不可用'})

        data['success'] = True
        data['errCount'] = len(data['error'])

        resp.body = json.dumps(data, ensure_ascii=False)


class UpdateSMTProductCategory():
    def on_get(self, req, resp):
        data = dict()
        data['success'] = False
        data['err'] = []

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        foo = db.productList.distinct('categoryId', {'categoryName': {'$exists': 0}})
        for item in foo:
            cate = db.aeopPostCategoryList.find_one({'id': item})
            if cate:
                print(cate['id'])
                print(db.productList.find({'categoryId': item}).count())
                db.productList.update({'categoryId': item}, {'$set': {'categoryName': cate['names']['zh']}}, multi=True)
            else:
                app = db.appList.find_one({'platform': 'aliexpress', 'apiInfo.status': 1})
                if app != None:
                    api = ALIEXPRESS(app)
                    c = api.getPostCategoryById(item)
                    try:
                        d = json.loads(c)
                        if d.has_key('aeopPostCategoryList'):
                            for c0 in d['aeopPostCategoryList']:
                                if db.aeopPostCategoryList.find({'id': c0['id']}).count() < 1:
                                    db.aeopPostCategoryList.insert(c0)
                            db.productList.update({'categoryId': item}, {
                                '$set': {'categoryName': d['aeopPostCategoryList'][0]['names']['zh']}}, multi=True)

                    except:
                        data['err'].append(item)
                else:
                    data['err'].append(item)

        data['success'] = True
        resp.body = json.dumps(data, ensure_ascii=False)


class GetAllProductCategory():
    def on_get(self, req, resp):
        data = dict()
        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        params = req._params
        if params.has_key('cateId'):
            cateId = params['cateId']
        else:
            cateId = 0

        try:
            cateId = int(cateId)
        except:
            cateId = 0

        data['errCount'] = 0

        app = db.appList.find_one({'platform': 'aliexpress', 'apiInfo.status': 1})
        if app != None:
            api = ALIEXPRESS(app)
            c = api.getChildrenPostCategoryById(cateId)
            try:
                d = json.loads(c)
                if d.has_key('aeopPostCategoryList'):
                    for topCate in d['aeopPostCategoryList']:
                        if db.aeopPostCategoryList.find({'id': topCate['id']}).count() < 1:
                            db.aeopPostCategoryList.insert(topCate)
                        if topCate['isleaf'] == False:
                            c2 = api.getChildrenPostCategoryById(topCate['id'])
                            try:
                                d2 = json.loads(c2)
                                if d2.has_key('aeopPostCategoryList'):
                                    for towCate in d2['aeopPostCategoryList']:
                                        if db.aeopPostCategoryList.find({'id': towCate['id']}).count() < 1:
                                            db.aeopPostCategoryList.insert(towCate)

                                        if towCate['isleaf'] == False:
                                            c3 = api.getChildrenPostCategoryById(towCate['id'])
                                            try:
                                                d3 = json.loads(c3)
                                                if d3.has_key('aeopPostCategoryList'):
                                                    for threeCate in d3['aeopPostCategoryList']:
                                                        if db.aeopPostCategoryList.find(
                                                                {'id': threeCate['id']}).count() < 1:
                                                            db.aeopPostCategoryList.insert(threeCate)

                                                        if threeCate['isleaf'] == False:
                                                            c4 = api.getChildrenPostCategoryById(threeCate['id'])
                                                            try:
                                                                d4 = json.loads(c4)
                                                                if d4.has_key('aeopPostCategoryList'):
                                                                    for fourthCate in d4['aeopPostCategoryList']:
                                                                        if db.aeopPostCategoryList.find(
                                                                                {'id': fourthCate['id']}).count() < 1:
                                                                            db.aeopPostCategoryList.insert(fourthCate)

                                                            except:
                                                                data['errCount'] += 1


                                            except:
                                                data['errCount'] += 1

                            except:
                                data['errCount'] += 1
            except:
                data['errCount'] += 1

        resp.body = json.dumps(data, ensure_ascii=False)


class CheckJDOrder():
    def on_get(self, req, resp):
        params = req._params
        if params.has_key('shop'):
            shopId = params['shop']
        else:
            shopId = ''
        if params.has_key('status'):
            status = params['status']
        else:
            status = ''
        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.jingdong

        appList = db.shopInfo.find()
        if shopId == '':
            app = appList[random.randint(0, appList.count() - 1)]
        else:
            app = db.shopInfo.find_one({'shopId': shopId})

        if app != None:
            api = JDAPI(app['apiInfo'])

            if status == '':
                statusList = ['WAIT_SELLER_STOCK_OUT', 'WAIT_GOODS_RECEIVE_CONFIRM', 'TRADE_CANCELED']
            else:
                statusList = status.strip(',').strip().split(',')

            total = 0
            addCount = 0
            updateCount = 0

            for s in statusList:
                result = api.getOrderList(order_state=s)
                try:
                    ol = result['order_search_response']['order_search']['order_info_list']
                except:
                    ol = []
                for od in ol:
                    item = od
                    item['createTime'] = datetime.datetime.now()
                    item['updateTime'] = None
                    item['dealCompleteTime'] = None
                    item['purchaseInfo'] = None
                    item['dealRemark'] = None
                    item['logisticsInfo'] = None
                    item['shopId'] = app['shopId']
                    item['platform'] = 'jingdong'
                    if not item.has_key('payment_confirm_time'):
                        item['payment_confirm_time'] = None
                    if not item.has_key('parent_order_id'):
                        item['parent_order_id'] = None
                    if not item.has_key('pin'):
                        item['pin'] = None
                    if not item.has_key('return_order'):
                        item['return_order'] = None
                    if not item.has_key('order_state_remark'):
                        item['order_state_remark'] = None
                    if not item.has_key('vender_remark'):
                        item['vender_remark'] = None

                    item['dealStatus'] = 0
                    item['stage'] = 0
                    item['oprationLog'] = []

                    for sku in item['item_info_list']:
                        sku['skuImg'] = None
                        sku['link'] = None
                        if not sku.has_key('product_no'):
                            sku['product_no'] = None
                        if not sku.has_key('outer_sku_id'):
                            sku['outer_sku_id'] = None
                        if not sku.has_key('ware_id'):
                            sku['ware_id'] = None

                    if db.orderList.find({'order_id': item['order_id']}).count() > 0:
                        updateCount += 1
                    else:
                        db.orderList.insert(item)
                    addCount += 1

                    total += 1

            respon = {'success': True, "data": {"total": total, "addCount": addCount, 'updateCount': updateCount}}
        else:
            respon = {'success': False}

        resp.body = json.dumps(respon, ensure_ascii=False)

class CheckPurchaseOrder():
    def on_get(self, req, resp):
        params = req._params
        if params.has_key('key'):
            key = params['key']
        else:
            key = ''

        data = dict()

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.woderp

        appList = db.appList.find({'platform': '1688'})

        if key == '':
            app = appList[random.randint(0, appList.count() - 1)]
        else:
            app = db.appList.find_one({'platform': '1688', 'appKey': key})

        if app != None:
            data['total'] = 0
            data['addCount'] = 0
            data['success'] = False

            api = ALIBABA(app)

            if params.has_key('orderStatus'):
                orderStatus = params['orderStatus']
            else:
                orderStatus = ''
            if params.has_key('pageNO'):
                pageNO = params['pageNO']
            else:
                pageNO = '1'
            if params.has_key('createStartTime'):
                createStartTime = params['createStartTime']
            else:
                createStartTime = ''
            if params.has_key('createEndTime'):
                createEndTime = params['createEndTime']
            else:
                createEndTime = ''

            option = {'pageNO': pageNO}
            if orderStatus != '':
                option['orderStatus'] = orderStatus
            if createStartTime != '':
                option['createStartTime'] = createStartTime
            else:
                option['createStartTime'] = (datetime.datetime.now() + datetime.timedelta(days=-1)).strftime(
                    '%Y-%m-%d %H:%M:%S')
            if createEndTime != '':
                option['createEndTime'] = createEndTime
            else:
                option['createEndTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            d = json.loads(api.getOrderList(option))

            if d.has_key('result') and d['result']['success']:
                ol = d['result']['toReturn']
                for od in ol:
                    item = od
                    item['createTime'] = datetime.datetime.now()
                    item['updateTime'] = None
                    item['appKey'] = app['appKey']
                    item['dealCompleteTime'] = None
                    item['dealRemark'] = None

                    item['dealStatus'] = 0
                    item['stage'] = 0
                    item['oprationLog'] = []

                    if db.purchaseList.find({'id': int(item['id'])}).count() > 0:
                        pass
                    else:
                        db.purchaseList.insert(item)
                        data['addCount'] += 1

                    data['total'] += 1

                data['success'] = True
            else:
                data['success'] = False

        else:
            data['success'] = False

        resp.body = json.dumps(data, ensure_ascii=False)