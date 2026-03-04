package com.cantor.api.controller;

import cn.hutool.core.util.StrUtil;
import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.cantor.common.core.util.R;
import com.cantor.common.security.annotation.CheckPermission;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * 云手机管理Controller
 * 集成启朔云手机RTC推流服务
 */
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/cloudphone")
public class CloudPhoneController {

    @Value("${cloudphone.signaling.url:https://hfcxsig.cheersucloud.com:8443}")
    private String signalingUrl;

    @Value("${cloudphone.ak:}")
    private String ak;

    @Value("${cloudphone.sk:}")
    private String sk;

    /**
     * 获取云手机连接用的加密串
     * 调用信令服务API获取连接凭证
     */
    @PostMapping("/encrypted-key")
    @CheckPermission("cloudphone:connect")
    public R<Map<String, Object>> getEncryptedKey(@RequestBody Map<String, Object> params) {
        try {
            String instanceId = (String) params.get("instanceId");
            if (StrUtil.isBlank(instanceId)) {
                return R.failed("实例ID不能为空");
            }

            // 使用正确的签名算法调用信令服务
            Map<String, Object> result = callSignalingApi(instanceId);
            
            if (result == null) {
                return R.failed("获取加密串失败");
            }

            return R.ok(result);

        } catch (Exception e) {
            log.error("获取加密串异常", e);
            return R.failed("获取加密串失败: " + e.getMessage());
        }
    }

    /**
     * 调用信令服务API
     * 使用HmacSHA1签名算法
     */
    private Map<String, Object> callSignalingApi(String instanceId) throws Exception {
        // 构建请求参数
        long timestamp = System.currentTimeMillis() / 1000;  // 秒级时间戳
        int nonce = new Random().nextInt(1000000);
        
        // data参数
        Map<String, Object> dataMap = new HashMap<>();
        dataMap.put("containerId", instanceId);  // 注意：使用containerId而不是instanceId
        String dataStr = JSONUtil.toJsonStr(dataMap);
        
        // 构建paramsMap (TreeMap按字母排序)
        Map<String, Object> paramsMap = new TreeMap<>();
        paramsMap.put("appId", ak);
        paramsMap.put("data", dataStr);
        paramsMap.put("nonce", nonce);
        paramsMap.put("timestamp", timestamp);
        
        // 构建待签名字符串
        StringBuilder plainStr = new StringBuilder();
        boolean first = true;
        for (Map.Entry<String, Object> entry : paramsMap.entrySet()) {
            if (!first) {
                plainStr.append("&");
            }
            plainStr.append(entry.getKey()).append("=").append(entry.getValue());
            first = false;
        }
        
        log.debug("待签名字符串: {}", plainStr);
        
        // HmacSHA1签名 (不是SHA256!)
        Mac mac = Mac.getInstance("HmacSHA1");
        SecretKeySpec secretKeySpec = new SecretKeySpec(sk.getBytes(StandardCharsets.UTF_8), "HmacSHA1");
        mac.init(secretKeySpec);
        byte[] signatureBytes = mac.doFinal(plainStr.toString().getBytes(StandardCharsets.UTF_8));
        String signature = Base64.getEncoder().encodeToString(signatureBytes);
        
        log.debug("签名: {}", signature);
        
        // 添加签名到参数
        paramsMap.put("signature", signature);
        
        // 调用信令服务API
        String url = signalingUrl + "/coordinate/api/v2/cstreaming/register";
        log.info("调用信令服务: instanceId={}, url={}", instanceId, url);
        
        HttpResponse response = HttpRequest.post(url)
                .header("Content-Type", "application/json")
                .body(JSONUtil.toJsonStr(paramsMap))
                .timeout(30000)
                .execute();
        
        if (response.getStatus() != 200) {
            log.error("信令服务返回错误: status={}, body={}", response.getStatus(), response.body());
            return null;
        }
        
        JSONObject result = JSONUtil.parseObj(response.body());
        if (result.getInt("code") != 0) {
            log.error("信令服务业务错误: {}", result.getStr("msg"));
            return null;
        }
        
        // 提取连接信息
        JSONObject data = result.getJSONObject("data");
        Map<String, Object> resultData = new HashMap<>();
        resultData.put("signalingServices", data.getJSONArray("signalingServices"));
        resultData.put("secretKey", data.getStr("secretKey"));
        resultData.put("containerID", data.getStr("containerID"));
        resultData.put("roomID", data.getStr("roomID"));
        resultData.put("peerID", data.getStr("peerID"));
        resultData.put("iceServers", data.getJSONArray("iceServers"));
        
        // 构建加密串(前端SDK需要)
        String encryptedKey = buildEncryptedKey(data);
        resultData.put("encryptedKey", encryptedKey);
        
        log.info("获取加密串成功: instanceId={}, roomId={}", instanceId, data.getStr("roomID"));
        return resultData;
    }
    
    /**
     * 构建加密串(前端SDK格式)
     */
    private String buildEncryptedKey(JSONObject data) {
        Map<String, Object> encryptedData = new HashMap<>();
        
        Map<String, Object> connectInfo = new HashMap<>();
        connectInfo.put("containerId", data.getStr("containerID"));
        connectInfo.put("roomID", data.getStr("roomID"));
        connectInfo.put("peerID", data.getStr("peerID"));
        connectInfo.put("cstreamingBuildVersion", "");
        connectInfo.put("signalingServices", data.getJSONArray("signalingServices"));
        connectInfo.put("iceServers", data.getJSONArray("iceServers"));
        
        Map<String, Object> mediaInfo = new HashMap<>();
        Map<String, Object> screen = new HashMap<>();
        screen.put("frameRate", 60);
        screen.put("targetBitrate", 8000);
        screen.put("startBitrate", 8000);
        screen.put("minBitrate", 6000);
        screen.put("maxBitrate", 12000);
        screen.put("width", 1080);
        screen.put("height", 1920);
        screen.put("adptTermResolutionFlag", 0);
        screen.put("codecName", "H264");
        screen.put("imageQuality", 1);
        screen.put("mode", 1);
        screen.put("scale", 1.0);
        mediaInfo.put("screen", screen);
        
        Map<String, Object> verify = new HashMap<>();
        verify.put("header", "X-Access-Token");
        verify.put("accessToken", data.getStr("secretKey"));
        
        encryptedData.put("connectInfo", connectInfo);
        encryptedData.put("mediaInfo", mediaInfo);
        encryptedData.put("verify", verify);
        encryptedData.put("traceId", UUID.randomUUID().toString());
        
        return Base64.getEncoder().encodeToString(JSONUtil.toJsonStr(encryptedData).getBytes());
    }

    /**
     * 获取可用的云手机实例列表
     * 这里应该从IaaS平台获取，暂时返回空列表
     */
    @GetMapping("/instances")
    @CheckPermission("cloudphone:list")
    public R<List<Map<String, Object>>> getInstances() {
        // TODO: 从IaaS平台获取实例列表
        List<Map<String, Object>> instances = new ArrayList<>();
        return R.ok(instances);
    }
}
