<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;
use App\Enums\SubscriptionType;

class CreateBoard extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('boards', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->timestamps();
            $table->string('name')->unique();
            $table->string('readable_name');
            $table->unsignedTinyInteger('type')->nullable();
            $table->unsignedBigInteger('created_by'); // FK->users
            $table->unsignedBigInteger('tower_id')->nullable(); // FK->towers
            $table->string('website_url')->nullable();
            $table->string('address')->nullable();
            $table->string('postcode')->nullable();
            $table->float('latitude', 9, 6)->nullable();
            $table->float('longitude', 9, 6)->nullable();
            $table->unsignedTinyInteger('can_post')->default(SubscriptionType::ADMIN);

            $table->softDeletes();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('boards');
    }
}
