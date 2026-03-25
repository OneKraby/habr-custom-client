package com.kraby.habr

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

// Model
data class Article(
    val title: String,
    val url: String,
    val date: String,
    val score: Int
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            // Very simple custom dark theme
            val darkColorScheme = darkColorScheme(
                background = Color(0xFF121212),
                surface = Color(0xFF1E1E1E),
                onBackground = Color.White,
                onSurface = Color.White
            )

            MaterialTheme(colorScheme = darkColorScheme) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen()
                }
            }
        }
    }
}

@Composable
fun MainScreen() {
    var articles by remember { mutableStateOf<List<Article>>(emptyList()) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    // Load top daily initially
    LaunchedEffect(Unit) {
        isLoading = true
        fetchData("http://10.0.2.2:8000/api/top?period=daily") { result, err ->
            isLoading = false
            if (err != null) errorMessage = err else articles = result
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            text = "Habr Custom (Top Daily)",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onBackground,
            modifier = Modifier.padding(bottom = 16.dp)
        )

        Row(
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            Button(onClick = {
                scope.launch {
                    isLoading = true; errorMessage = null
                    fetchData("http://10.0.2.2:8000/api/top?period=daily") { result, err ->
                        isLoading = false
                        if (err != null) errorMessage = err else articles = result
                    }
                }
            }) { Text("Top Daily") }

            Button(onClick = {
                scope.launch {
                    isLoading = true; errorMessage = null
                    fetchData("http://10.0.2.2:8000/api/custom?start=2024-01-01&end=2024-03-01&sort=antitop") { result, err ->
                        isLoading = false
                        if (err != null) errorMessage = err else articles = result
                    }
                }
            }) { Text("Anti-Top Example") }
        }

        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else if (errorMessage != null) {
            Text(text = "Error: $errorMessage", color = Color.Red)
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(articles) { article ->
                    ArticleCard(article)
                }
            }
        }
    }
}

@Composable
fun ArticleCard(article: Article) {
    val context = LocalContext.current
    val scoreColor = if (article.score > 0) Color(0xFF4CAF50) else if (article.score < 0) Color(0xFFF44336) else Color.Gray

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.surface)
            .clickable {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(article.url))
                context.startActivity(intent)
            }
            .padding(16.dp)
    ) {
        Column {
            Text(
                text = article.title,
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = article.date,
                    fontSize = 14.sp,
                    color = Color.Gray
                )
                Text(
                    text = if (article.score > 0) "+${article.score}" else "${article.score}",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = scoreColor
                )
            }
        }
    }
}

// Background network request function
suspend fun fetchData(url: String, callback: (List<Article>, String?) -> Unit) {
    withContext(Dispatchers.IO) {
        val client = OkHttpClient()
        val request = Request.Builder().url(url).build()

        try {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    withContext(Dispatchers.Main) { callback(emptyList(), "HTTP ${response.code}") }
                    return@use
                }
                val responseData = response.body?.string()
                if (responseData != null) {
                    val listType = object : TypeToken<List<Article>>() {}.type
                    val articles: List<Article> = Gson().fromJson(responseData, listType)
                    withContext(Dispatchers.Main) { callback(articles, null) }
                } else {
                    withContext(Dispatchers.Main) { callback(emptyList(), "Empty response") }
                }
            }
        } catch (e: IOException) {
            withContext(Dispatchers.Main) { callback(emptyList(), e.message) }
        }
    }
}
